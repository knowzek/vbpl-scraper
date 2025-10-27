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
import json
import requests
from zoneinfo import ZoneInfo
EASTERN = ZoneInfo("America/New_York")

def _ics_to_local(dtstr: str, params: str = ""):
    """
    Convert an iCal datetime string into America/New_York local time.
    WithApps quirk: timestamps often include TZID=America/New_York but
    the *clock* is actually UTC. We detect that and convert UTC->Eastern.
    Rules:
      - Ends with 'Z'              -> UTC -> Eastern
      - TZID=America/New_York      -> treat clock as UTC -> Eastern  (quirk)
      - Other TZID                 -> use that tz -> Eastern
      - Timed, no Z/TZID           -> assume UTC -> Eastern          (quirk)
      - Date-only (no time)        -> keep date in local
    """
    if not dtstr:
        return None

    s = dtstr.strip()
    m = re.match(r"^(\d{4})(\d{2})(\d{2})(?:T(\d{2})(\d{2})(\d{2})?)?(Z)?$", s)
    if not m:
        return None

    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    hh = int(m.group(4) or 0)
    mm = int(m.group(5) or 0)
    has_time = m.group(4) is not None
    has_z = bool(m.group(7))

    # Extract TZID param if present
    tzid = ""
    m_tz = re.search(r"(?:^|;)TZID=([^;:]+)", params or "", re.I)
    if m_tz:
        tzid = m_tz.group(1).strip()

    # --- handling ---
    if has_z:
        # UTC explicitly -> convert to Eastern
        aware = dt.datetime(y, mo, d, hh, mm, tzinfo=dt.timezone.utc)
        return aware.astimezone(EASTERN)

    if tzid:
        if tzid.lower() in ("america/new_york", "us/eastern") and has_time:
            # 🔧 WithApps quirk: clock is UTC even though TZID says Eastern
            aware = dt.datetime(y, mo, d, hh, mm, tzinfo=dt.timezone.utc)
            return aware.astimezone(EASTERN)
        # Any other real TZID: respect it, then show in Eastern
        try:
            src = ZoneInfo(tzid)
        except Exception:
            src = EASTERN
        return dt.datetime(y, mo, d, hh, mm, tzinfo=src).astimezone(EASTERN)

    if has_time:
        # Timed, no Z/TZID: WithApps usually means UTC
        aware = dt.datetime(y, mo, d, hh, mm, tzinfo=dt.timezone.utc)
        return aware.astimezone(EASTERN)

    # Date-only
    return dt.datetime(y, mo, d)



BASE_ICS = "https://api.withapps.io/api/v2/organizations/30/calendar/ical"
AUDIENCE_FILTERS = ["Kids", "Family", "Youth"]
LIBRARY_KEY = "visithampton"

# --- PAGE PARSERS (robust for calendar.hampton.gov) ---
_HTML_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.I | re.S)
_H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
_META_DESC_RE = re.compile(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']', re.I)
_SITE_NAME_RE = re.compile(r'<meta\s+property=["\']og:site_name["\']\s+content=["\']([^"\']+)["\']', re.I)

# strip tags but preserve newlines between block elements
_BLOCK_TAGS = re.compile(r"</?(p|div|br|li|ul|ol|section|article|h\d)[^>]*>", re.I)
_TAG_RE = re.compile(r"<[^>]+>")

def _parse_from_ldjson(html_text: str) -> dict:
    """
    Return dict with keys that might exist: name, venue, start, end.
    Parses <script type="application/ld+json"> blocks and looks for @type=Event.
    """
    out = {"name": "", "venue": "", "start": "", "end": ""}
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                         html_text, re.I | re.S):
        raw = m.group(1).strip()
        try:
            data = json.loads(raw)
        except Exception:
            continue

        # data can be dict or list
        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if not isinstance(item, dict):
                continue
            t = (item.get("@type") or item.get("type") or "")
            if isinstance(t, list):
                t = ",".join(t)
            if "Event" not in str(t):
                continue

            # name
            if not out["name"]:
                out["name"] = (item.get("name") or "").strip()

            # venue (location.name or location.@type=Place)
            loc = item.get("location")
            if loc and not out["venue"]:
                if isinstance(loc, list):
                    for L in loc:
                        nm = (L.get("name") or "").strip() if isinstance(L, dict) else ""
                        if nm:
                            out["venue"] = nm
                            break
                elif isinstance(loc, dict):
                    nm = (loc.get("name") or "").strip()
                    if nm:
                        out["venue"] = nm

            # times
            out["start"] = out["start"] or (item.get("startDate") or "").strip()
            out["end"] = out["end"] or (item.get("endDate") or "").strip()

            # if we’ve got a name and either venue or time, that’s good enough
            if out["name"] and (out["venue"] or out["start"]):
                return out
    return out


def _parse_time_from_page(html_text: str) -> str:
    # e.g. <div class="activity-time bold">03:30 PM - 04:00 PM</div>
    m = re.search(r'<div[^>]*class="[^"]*activity-time[^"]*bold[^"]*"[^>]*>(.*?)</div>',
                  html_text, re.I | re.S)
    if m:
        txt = _clean_html_text(m.group(1))
        return re.sub(r"\s*-\s*", " – ", txt)
    return ""


def _clean_html_text(html_text: str) -> str:
    txt = _BLOCK_TAGS.sub("\n", html_text)
    txt = _TAG_RE.sub("", txt)
    txt = html.unescape(txt)
    txt = re.sub(r"[ \t\u00A0]+", " ", txt)
    txt = re.sub(r"\n\s*\n\s*\n+", "\n\n", txt)
    return txt.strip()

def _fetch_event_page(url: str, timeout: int = 12) -> str:
    if not url:
        return ""
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code == 200 and "text/html" in r.headers.get("Content-Type",""):
            return r.text
    except Exception:
        pass
    return ""

def _parse_name_from_page(html_text: str) -> str:
    # Exact block: <div class="home-title"><h1>...</h1></div>
    m = re.search(r'<div[^>]*class="[^"]*home-title[^"]*"[^>]*>.*?<h1[^>]*>(.*?)</h1>',
                  html_text, re.I | re.S)
    if m:
        return _clean_html_text(m.group(1))
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html_text, re.I | re.S)
    if m:
        return _clean_html_text(m.group(1))
    m = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html_text, re.I)
    if m:
        return html.unescape(m.group(1)).strip()
    m = re.search(r"<title>(.*?)</title>", html_text, re.I | re.S)
    if m:
        return _clean_html_text(m.group(1)).split(" | ")[0]
    return ""


def _parse_desc_from_page(html_text: str) -> str:
    # Target the block in your screenshot: .section-activity-text .text
    m = re.search(r'<section[^>]*class="[^"]*section-activity-text[^"]*"[^>]*>(.*?)</section>', html_text, re.I | re.S)
    if m:
        return _clean_html_text(m.group(1))
    # Fallback to meta description
    m = _META_DESC_RE.search(html_text)
    if m:
        return html.unescape(m.group(1)).strip()
    return ""

def _extract_venue(detail_html: str) -> str:
    """Pick a venue from the page's Tags list; ignore 'Close' and age tags."""
    if not detail_html:
        return ""
    m = re.search(r'<ul[^>]*class="[^"]*tags-list[^"]*"[^>]*>(.*?)</ul>', detail_html, re.I | re.S)
    if not m:
        return ""
    spans = re.findall(r"<span[^>]*>(.*?)</span>", m.group(1), re.I | re.S)

    cands = []
    for raw in spans:
        v = _clean_html_text(raw)
        if not v:
            continue
        vl = v.lower()
        if vl == "close":
            continue
        if re.search(r"\b(ages?|grades?)\b", vl):
            continue
        cands.append(v)

    if not cands:
        return ""

    pri = ("library","center","museum","park","theatre","theater","hall",
           "gallery","visitor","community","fort","rec","recreation","ymca")
    def score(x: str):
        xl = x.lower()
        hits = sum(p in xl for p in pri)
        return (-hits, len(x))
    return sorted(dict.fromkeys(cands), key=score)[0]
def _venue_from_title(title: str) -> str:
    """Pull venue from '... at Phoebus Library (Hampton)' style titles."""
    m = re.search(r"\bat\s+(.+?)\s*\(Hampton\)\s*$", (title or ""), re.I)
    return m.group(1).strip() if m else ""

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

def _fmt_date_parts(dtstart: str, start_params: str = ""):
    local = _ics_to_local(dtstart, start_params)
    if not local:
        return "", "", ""
    local = local.astimezone(EASTERN)  # ✅ ensure local conversion
    return local.strftime("%b"), str(local.day), str(local.year)


def _fmt_time_range(dtstart: str, dtend: str, start_params: str = "", end_params: str = ""):
    st = _ics_to_local(dtstart, start_params)
    en = _ics_to_local(dtend, end_params) if dtend else None
    if not st and not en:
        return ""
    if st and not en:
        en = st + dt.timedelta(hours=1)
    # ✅ ensure both are in Eastern local time
    st = st.astimezone(EASTERN)
    en = en.astimezone(EASTERN) if en else None

    def fmt(x: dt.datetime) -> str:
        return x.strftime("%-I:%M %p").lstrip("0")

    return f"{fmt(st)} - {fmt(en)}" if en else fmt(st)


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
    url = _extract_url(evt).strip()

    # Pull the page once (most reliable source)
    page_html = _fetch_event_page(url) if url else ""

    # Try JSON-LD first (very reliable on With pages)
    ld = _parse_from_ldjson(page_html) if page_html else {"name":"","venue":"","start":"","end":""}

    # NAME: prefer page H1 → JSON-LD → cleaned SUMMARY → raw SUMMARY → first desc line
    name = _parse_name_from_page(page_html) if page_html else ""
    if not name:
        name = (ld.get("name") or "").strip()
    if not name:
        name = _clean_summary(raw_summary)

    # DESCRIPTION: prefer page block; then X-ALT-DESC; then DESCRIPTION
    desc = _parse_desc_from_page(page_html) if page_html else ""
    if not desc:
        desc = _preferred_description(evt)
    if not name:
        first = next((ln.strip() for ln in (desc or "").splitlines() if ln.strip()), "")
        name = first[:120] if first else "Community Event"

    # VENUE: page tags → JSON-LD → title fallback
    venue = _extract_venue(page_html) if page_html else ""
    if not venue:
        venue = (ld.get("venue") or "").strip()
    if not venue:
        venue = _venue_from_title(name)

    # Build display title AFTER venue is known
    final_title = name
    if venue and not re.search(r"\bat\s+.+\(\s*Hampton\s*\)\s*$", name, re.I):
        final_title = f"{name} at {venue} (Hampton)"

    # LOCATION (sheet column): prefer venue; fall back to ICS LOCATION (address)
    location_prop = (evt.get("LOCATION") or "").replace("\\,", ",").strip()
    location_for_sheet = venue or location_prop or ""
    if not venue and location_prop:
        desc = f"{desc}\n\nAddress: {location_prop}" if desc else f"Address: {location_prop}"

    # DATE/TIME
    month, day, year = _fmt_date_parts(evt.get("DTSTART", ""), evt.get("__DTSTART_params", ""))

    time_str = _fmt_time_range(
        evt.get("DTSTART", ""),
        evt.get("DTEND",   ""),
        evt.get("__DTSTART_params", ""),
        evt.get("__DTEND_params",   "")
    )

    # fallback: pull time from page if ICS had none; then JSON-LD
    if not time_str and page_html:
        page_time = _parse_time_from_page(page_html)
        if page_time:
            time_str = page_time
    if not time_str and (ld.get("start") or ld.get("end")):
        def _fmt_iso(t):
            m = re.search(r"T(\d{2}):(\d{2})", t or "")
            if not m: return ""
            hh, mm = int(m.group(1)), int(m.group(2))
            ampm = "am" if hh < 12 else "pm"
            h = (hh % 12) or 12
            return f"{h}{ampm}" if mm == 0 else f"{h}:{mm:02d}{ampm}"
        st = _fmt_iso(ld.get("start") or "")
        en = _fmt_iso(ld.get("end") or "")
        time_str = f"{st} – {en}".strip(" –") if (st or en) else time_str

    # Categories & Ages
    cats = _split_categories(evt)
    ages = detect_ages(name, desc, cats)
    categories = set(["Event Location - Hampton"])
    if not ages:
        categories.add("Audience - Family Event")

    # Debug prints
    if page_html == "":
        print(f"[vh] empty HTML → {url}")
    if not name:
        print(f"[vh] name missing → {url}")
    if not venue:
        print(f"[vh] venue missing → {url}")
    if not time_str:
        print(f"[vh] time missing → {url}")

    if os.getenv("DEBUG_VH") == "1":
        print(f"[vh] ok? name={bool(name)} time={bool(time_str)} venue={bool(venue)} "
              f"ld.name={bool(ld.get('name'))} ld.venue={bool(ld.get('venue'))} "
              f"url={url}")
        
    print("DBG DTSTART:", evt.get("DTSTART"), evt.get("__DTSTART_params"))
    print("DBG DTEND:",   evt.get("DTEND"),   evt.get("__DTEND_params"))

    return {
        "UID": (evt.get("UID") or "").strip(),
        "_url": url,
        "_categories": list(categories.union(set(cats))),
        "_ages": ages,

        "Event Link": url,
        "Event Name": final_title,
        "Description": desc,
        "Event Status": "Available",
        "Time": time_str,
        "Ages": ", ".join(ages) if ages else "",
        "Location": location_for_sheet,   # <-- this is what your sheet uses
        "Venue": venue,
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
        for k in ("Event Name","Description","Location","Time","Ages","Categories"):
            if k in e and isinstance(e[k], str):
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
        upload_events_to_sheet(rows, library=LIBRARY_KEY, mode=mode)
        print(f"✅ Upload attempted for {LIBRARY_KEY}. Prepared {len(rows)} rows.")

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
