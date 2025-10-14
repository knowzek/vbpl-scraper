# scrape_visithampton_hmva_ical.py (fixed: title, venue, description)
from __future__ import annotations
import argparse
import datetime as dt
import html
import os
import re
import sys
import time
import urllib.parse
from typing import Dict, List, Tuple, Optional

import requests

BASE_ICS = "https://api.withapps.io/api/v2/organizations/30/calendar/ical"
AUDIENCE_FILTERS = ["Kids", "Family", "Youth"]
LIBRARY_KEY = "visithampton"

def _unix(t: dt.datetime) -> int:
    return int(t.timestamp())

def _time_window(weeks: int) -> Tuple[int, int]:
    now = dt.datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + dt.timedelta(weeks=weeks)
    return _unix(start), _unix(end)

# ---------- ICS parsing (keep params for X-APPLE-STRUCTURED-LOCATION) ----------
def _unfold_ics_lines(text: str) -> List[str]:
    raw_lines = text.splitlines()
    out = []
    for line in raw_lines:
        if not out:
            out.append(line.rstrip("\r\n"))
            continue
        if line.startswith((" ", "\t")):
            out[-1] += line[1:]
        else:
            out.append(line.rstrip("\r\n"))
    return out

def _parse_vevent_blocks(ics_text: str) -> List[Dict[str, str]]:
    lines = _unfold_ics_lines(ics_text)
    events = []
    cur = None
    for line in lines:
        if line.startswith("BEGIN:VEVENT"):
            cur = {}
        elif line.startswith("END:VEVENT"):
            if cur:
                events.append(cur)
                cur = None
        elif cur is not None and ":" in line:
            prop, value = line.split(":", 1)
            prop_name = prop.split(";", 1)[0].upper()
            cur.setdefault(prop_name, "")
            if cur[prop_name]:
                cur[prop_name] += "," + value
            else:
                cur[prop_name] = value
            # keep params for certain props
            if ";" in prop:
                cur[f"__{prop_name}_params"] = prop.split(";", 1)[1]
    return events

# ---------- Field helpers ----------
_MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

def _fmt_date_parts(dtstart: str) -> Tuple[str, str, str]:
    s = (dtstart or "").replace("Z", "")
    m = re.match(r"^(\d{4})(\d{2})(\d{2})", s)
    if not m:
        return "", "", ""
    year, mm, dd = m.group(1), m.group(2), m.group(3)
    month_name = _MONTHS[int(mm) - 1] if 1 <= int(mm) <= 12 else ""
    return month_name, str(int(dd)), year

def _fmt_time_range(dtstart: str, dtend: str) -> str:
    def parse_time(s: str) -> Optional[Tuple[int,int]]:
        s = (s or "").replace("Z", "")
        m = re.match(r"^\d{8}T(\d{2})(\d{2})", s)
        if not m:
            return None
        return int(m.group(1)), int(m.group(2))
    st = parse_time(dtstart)
    en = parse_time(dtend) if dtend else None
    if not st and not en:
        return ""
    def fmt(hh: int, mm: int) -> str:
        ampm = "am" if hh < 12 else "pm"
        h = hh % 12
        if h == 0:
            h = 12
        return f"{h}{ampm}" if mm == 0 else f"{h}:{mm:02d}{ampm}"
    if st and en:
        return f"{fmt(*st)} – {fmt(*en)}"
    if st:
        return fmt(*st)
    return ""

def _extract_url(evt: Dict[str, str]) -> str:
    for k in ("URL", "X-ALT-DESC", "X-WR-URL"):
        v = evt.get(k, "") or ""
        if isinstance(v, str) and v.startswith("http"):
            return v.strip()
    desc = evt.get("DESCRIPTION", "") or ""
    m = re.search(r"https?://\S+", desc)
    return m.group(0).rstrip(")>].,") if m else ""

def _split_categories(evt: Dict[str, str]) -> List[str]:
    raw = evt.get("CATEGORIES", "") or ""
    if not raw:
        return []
    parts = [p.replace(r"\,", ",").strip() for p in raw.split(",")]
    return [p for p in parts if p]

# ---------- Description: prefer HTML (X-ALT-DESC) ----------
_TAG_RE = re.compile(r"<[^>]+>")

def _preferred_description(evt: Dict[str, str]) -> str:
    raw_html = evt.get("X-ALT-DESC", "") or ""
    if raw_html:
        # ICS often encodes \n as literal \n, unescape twice
        txt = html.unescape(raw_html.replace("\\n", "\n"))
        txt = _TAG_RE.sub("", txt)
        return re.sub(r"\s+\n", "\n", txt).strip()
    # fallback to DESCRIPTION (unescape ICS escapes)
    desc = (evt.get("DESCRIPTION", "") or "").replace("\\n", "\n")
    return html.unescape(desc).strip()

# ---------- Venue name extraction ----------
def _venue_from_xapple(evt: Dict[str, str]) -> str:
    params = evt.get("__X-APPLE-STRUCTURED-LOCATION_params", "") or ""
    # look for X-TITLE=...; or TITLE=...
    m = re.search(r"(?:X-TITLE|TITLE)=([^;]+)", params)
    if m:
        return html.unescape(m.group(1)).replace("\\,", ",").strip()
    return ""

_HTML_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.I | re.S)
_META_RE = re.compile(r'<meta\s+[^>]*property=["\']og:(title|site_name)["\'][^>]*content=["\']([^"\']+)["\']', re.I)

def _fetch_page_title_and_venue(url: str, timeout: int = 12) -> Tuple[str,str]:
    """Lightweight HTML fetch to fix bad SUMMARY and venue name."""
    if not url:
        return "", ""
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code != 200 or "text/html" not in (r.headers.get("Content-Type","")):
            return "", ""
        html_text = r.text
        # og:title beats <title>
        og = _META_RE.findall(html_text)
        og_map = {k:v for (k,v) in og}
        title = og_map.get("title", "")
        if not title:
            m = _HTML_TITLE_RE.search(html_text)
            if m:
                title = html.unescape(m.group(1)).strip()
        venue = og_map.get("site_name", "")
        return (title.strip(), venue.strip())
    except Exception:
        return "", ""

# ---------- Age detection ----------
AGE_RULES = [
    (r"\b(babies|infants?|0-?12\s*months?|under\s*1)\b", "Babies (0-12 months)"),
    (r"\b(onesies|12-?24\s*months?|toddlers?)\b", "Onesies (12-24 months)"),
    (r"\b(pre[-\s]?k|pre[-\s]?school|ages?\s*3-?5|3[-–]5\s*years?)\b", "Preschool (3-5 years)"),
    (r"\bgrades?\s*(k|k-?1|k-?2|k-?3|k-?4|k-?5)\b|\belementary\b|\bages?\s*6-?10\b", "School Age"),
    (r"\bgrades?\s*3-?5\b|\bupper\s*elementary\b", "School Age"),
    (r"\b(grades?\s*6-?8|middle\s*school)\b", "Grades 6-8"),
    (r"\b(grades?\s*9-?12|high\s*school|teens?)\b", "Grades 9-12"),
    (r"\b(adults?\s*18\+|adult\s+only)\b", "Adults 18+"),
    (r"\ball\s*ages\b", "All Ages"),
]

def detect_ages(name: str, description: str, categories: List[str]) -> List[str]:
    text = f"{name}\n{description}\n{', '.join(categories)}".lower()
    hits = []
    for pattern, label in AGE_RULES:
        if re.search(pattern, text):
            hits.append(label)
    seen, ordered = set(), []
    for x in hits:
        if x not in seen:
            ordered.append(x); seen.add(x)
    return ordered

# ---------- Fetch & merge ----------
def build_ics_url(audience: str, start_unix: int, end_unix: int) -> str:
    params = [
        ("filterBy[startsAt]", str(start_unix)),
        ("filterBy[endsAt]", str(end_unix)),
        ("pinnedFilters[0]", audience),
    ]
    return BASE_ICS + "?" + urllib.parse.urlencode(params)

def fetch_ics(url: str, retries: int = 2, timeout: int = 30) -> str:
    last_err = None
    for _ in range(retries + 1):
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200 and "BEGIN:VCALENDAR" in r.text:
                return r.text
            last_err = f"HTTP {r.status_code}"
        except Exception as e:
            last_err = str(e)
        time.sleep(1.0)
    raise RuntimeError(f"Failed to fetch ICS: {last_err}")

def merge_events_by_uid(event_lists: List[List[Dict]]) -> List[Dict]:
    merged: Dict[str, Dict] = {}
    for lst in event_lists:
        for e in lst:
            uid = e.get("UID") or (e.get("_url","") + "|" + e.get("DTSTART",""))
            if uid in merged:
                old = merged[uid]
                old["_categories"] = list(set(old.get("_categories", [])) | set(e.get("_categories", [])))
                old["_ages"] = list(set(old.get("_ages", [])) | set(e.get("_ages", [])))
            else:
                merged[uid] = e
    return list(merged.values())

# ---------- Core event builder (fixed: name, venue, desc) ----------
_ADDR_LIKE = re.compile(r"\b(\d{2,5}\s+\w+)\b")  # crude address detector

def _clean_summary(summary: str) -> str:
    s = (summary or "").strip()
    # drop trailing " at …"
    s = re.sub(r"\s+at\s+.+$", "", s, flags=re.I).strip()
    # if it still begins with "at " it's junk
    if re.match(r"^at\s", s, flags=re.I):
        return ""
    return s

def _event_dict_from_vevent(evt: Dict[str, str], audience_hint: str) -> Dict:
    raw_summary = (evt.get("SUMMARY") or "").strip()
    name = _clean_summary(raw_summary)

    url = _extract_url(evt).strip()
    # if summary collapsed to empty, try from page
    if not name:
        page_title, _ = _fetch_page_title_and_venue(url)
        if page_title:
            # Some With titles look like "Event Name | Hampton, VA"
            name = re.split(r"\s+\|\s+", page_title)[0].strip()

    # description: prefer X-ALT-DESC (HTML)
    desc = _preferred_description(evt)

    # venue preference: X-APPLE… X-TITLE, else from page <meta site_name>, else from SUMMARY right-hand side, else None
    venue = _venue_from_xapple(evt)
    if not venue:
        _, site_name = _fetch_page_title_and_venue(url)
        if site_name and "hampton" not in site_name.lower():  # avoid generic "City of Hampton"
            venue = site_name.strip()
    if not venue and raw_summary:
        m = re.search(r"\s+at\s+(.+)$", raw_summary, flags=re.I)
        if m:
            cand = m.group(1).replace("\\,", ",").strip()
            if not _ADDR_LIKE.search(cand):  # use only if not an address
                venue = cand

    # if still no venue, last resort: LOCATION (but LOCATION is usually address; do NOT use it for title append)
    location_prop = (evt.get("LOCATION") or "").replace("\\,", ",").strip()
    # We'll expose address in description tail if venue unknown; but set Location to venue for uploader title appending
    location_for_title = venue or ""

    cats = _split_categories(evt)
    ages = detect_ages(name, desc, cats)

    categories = set(["Event Location - Hampton"])
    if not ages:
        categories.add("Audience - Family Event")

    month, day, year = _fmt_date_parts(evt.get("DTSTART",""))
    time_str = _fmt_time_range(evt.get("DTSTART",""), evt.get("DTEND",""))

    # If we still lack a decent name, synthesize from first line of desc
    if not name:
        first_line = (desc.splitlines()[0] if desc else "").strip()
        name = first_line[:120] if first_line else "Community Event"

    # If venue missing but LOCATION exists, append a short address hint into Description (not Location)
    if not venue and location_prop:
        if desc:
            desc = f"{desc}\n\nAddress: {location_prop}"
        else:
            desc = f"Address: {location_prop}"

    return {
        "UID": (evt.get("UID") or "").strip(),
        "_url": url,
        "_categories": list(categories.union(set(cats))),
        "_ages": ages,

        "Event Link": url,
        "Name": name,                       # uploader will append (Hampton)
        "Description": desc,
        "Event Status": "Available",
        "Event Time": time_str,
        "Ages": ", ".join(ages) if ages else "",
        "Location": location_for_title,     # <-- venue name for title append
        "Month": month,
        "Day": day,
        "Year": year,
        "Categories": ", ".join(sorted(categories.union(set(cats)))) if (categories or cats) else "",
        "Program Type": "",
        "Library": LIBRARY_KEY,
    }

def scrape_visithampton_hmva_ical(mode: str = "full") -> List[Dict]:
    weeks = 12 if mode == "full" else 4
    start_unix, end_unix = _time_window(weeks)

    all_lists: List[List[Dict]] = []
    for audience in AUDIENCE_FILTERS:
        url = build_ics_url(audience, start_unix, end_unix)
        ics_text = fetch_ics(url)
        vevents = _parse_vevent_blocks(ics_text)
        events_for_audience = []
        for v in vevents:
            ed = _event_dict_from_vevent(v, audience_hint=audience)
            events_for_audience.append(ed)
        all_lists.append(events_for_audience)

    merged = merge_events_by_uid(all_lists)

    def _strip_emojis(s: str) -> str:
        if not s:
            return s
        return re.sub(r"[\U00010000-\U0010FFFF]", "", s)
    for e in merged:
        for k in ("Name","Description","Location","Event Time","Ages","Categories"):
            e[k] = _strip_emojis(e.get(k, "")).strip()
    return merged

def _maybe_upload(rows: List[Dict], mode: str):
    try:
        from upload_to_sheets import upload_events_to_sheet  # type: ignore
    except Exception:
        print("Uploader not found; skipping Google Sheets upload.")
        print(f"Prepared {len(rows)} {LIBRARY_KEY} rows ({mode} mode).")
        return
    try:
        added, updated, skipped = upload_events_to_sheet(rows, library=LIBRARY_KEY, mode=mode)
        print(f"✅ Uploaded {LIBRARY_KEY}: +{added} new, ↻{updated} updated, ⏭ {skipped} skipped")
    except Exception as e:
        print(f"⚠️ Upload failed: {e}")
        print(f"Prepared {len(rows)} rows locally.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape VisitHampton (With iCal)")
    parser.add_argument("--mode", choices=["full","fast"], default="full",
                        help="full = next 12 weeks, fast = next 4 weeks")
    args = parser.parse_args()
    rows = scrape_visithampton_hmva_ical(mode=args.mode)
    _maybe_upload(rows, mode=args.mode)
