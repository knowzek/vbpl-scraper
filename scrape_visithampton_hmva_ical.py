# scrape_visithampton_hmva_ical.py
# Ready-to-paste scraper for Visit Hampton (With calendar via iCal)
# - Supports two timeframes: "full" (next 12 weeks) and "fast" (next 4 weeks)
# - Pulls three audience feeds: Kids, Family, Youth (server-side pinnedFilters if respected)
# - Parses ICS without external libs, dedupes by UID, unions categories
# - Derives Ages from description/title; if none found, tags as Family
# - Always adds "Event Location - Hampton" to categories
# - Emits rows compatible with your uploader. Will call upload_to_sheets if present.

from __future__ import annotations
import argparse
import datetime as dt
import os
import re
import sys
import time
import urllib.parse
import requests
from typing import Dict, List, Tuple, Optional

BASE_ICS = "https://api.withapps.io/api/v2/organizations/30/calendar/ical"

# Audience filters to attempt server-side
AUDIENCE_FILTERS = ["Kids", "Family", "Youth"]

# Library identifier (used by your uploader & constants)
LIBRARY_KEY = "visithampton"

# -----------------------------------------------------------------------------
# Time window helpers
# -----------------------------------------------------------------------------

def _unix(t: dt.datetime) -> int:
    return int(t.timestamp())

def _time_window(weeks: int) -> Tuple[int, int]:
    now = dt.datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + dt.timedelta(weeks=weeks)
    return _unix(start), _unix(end)

# -----------------------------------------------------------------------------
# Lightweight ICS parsing (no external libs)
# -----------------------------------------------------------------------------

def _unfold_ics_lines(text: str) -> List[str]:
    """Unfold folded iCal lines: lines that begin with space/tab are continuations."""
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
    """Parse ICS into a list of VEVENT dictionaries (key -> value)."""
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
        elif cur is not None:
            # Split property and value: e.g., "DTSTART;TZID=America/New_York:20251022T180000"
            if ":" not in line:
                continue
            prop, value = line.split(":", 1)
            prop_name = prop.split(";", 1)[0].upper()
            cur.setdefault(prop_name, "")
            # Some props can repeat (e.g., CATEGORIES)
            if cur[prop_name]:
                cur[prop_name] += "," + value
            else:
                cur[prop_name] = value
    return events

# -----------------------------------------------------------------------------
# Field normalization
# -----------------------------------------------------------------------------

_MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

def _fmt_date_parts(dtstart: str) -> Tuple[str, str, str]:
    """
    Accepts DTSTART like '20251022T180000' or '20251022' (with optional Z).
    Returns (MonthNameAbbrev, DayStr, YearStr) -> ('Oct','22','2025')
    """
    s = dtstart.replace("Z", "")
    m = re.match(r"^(\d{4})(\d{2})(\d{2})", s)
    if not m:
        return "", "", ""
    year, mm, dd = m.group(1), m.group(2), m.group(3)
    month_name = _MONTHS[int(mm) - 1] if 1 <= int(mm) <= 12 else ""
    return month_name, str(int(dd)), year

def _fmt_time_range(dtstart: str, dtend: str) -> str:
    """
    Convert to a human-ish 'h:mma – h:mma' or '' if all-day/unknown.
    We keep it simple; your uploader can re-normalize if needed.
    """
    def parse_time(s: str) -> Optional[Tuple[int,int]]:
        s = s.replace("Z", "")
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
        if mm == 0:
            return f"{h}{ampm}"
        return f"{h}:{mm:02d}{ampm}"
    if st and en:
        return f"{fmt(*st)} – {fmt(*en)}"
    if st and not en:
        return fmt(*st)
    return ""

def _extract_url(evt: Dict[str, str]) -> str:
    # Prefer URL prop; else find first http(s) in DESCRIPTION
    for k in ("URL", "X-ALT-DESC", "X-WR-URL"):
        v = evt.get(k, "")
        if v.startswith("http"):
            return v.strip()
    desc = evt.get("DESCRIPTION", "") or ""
    m = re.search(r"https?://\S+", desc)
    return m.group(0).rstrip(")>].,") if m else ""

def _split_categories(evt: Dict[str, str]) -> List[str]:
    raw = evt.get("CATEGORIES", "") or ""
    if not raw:
        return []
    # Categories can be comma-joined; also some ICS escape commas as '\,'
    parts = [p.replace(r"\,", ",").strip() for p in raw.split(",")]
    return [p for p in parts if p]

# -----------------------------------------------------------------------------
# Age/Audience detection from text (title + description)
# -----------------------------------------------------------------------------

AGE_RULES = [
    # Babies / Toddlers
    (r"\b(babies|infants?|0-?12\s*months?|under\s*1)\b", "Babies (0-12 months)"),
    (r"\b(onesies|12-?24\s*months?|toddlers?)\b", "Onesies (12-24 months)"),
    # Preschool
    (r"\b(pre[-\s]?k|pre[-\s]?school|ages?\s*3-?5|3[-–]5\s*years?)\b", "Preschool (3-5 years)"),
    # School age
    (r"\bgrades?\s*(k|k-?1|k-?2|k-?3|k-?4|k-?5)\b|\belementary\b|\bages?\s*6-?10\b", "School Age"),
    (r"\bgrades?\s*3-?5\b|\bupper\s*elementary\b", "School Age"),
    # Teens / Middle & High
    (r"\b(grades?\s*6-?8|middle\s*school)\b", "Grades 6-8"),
    (r"\b(grades?\s*9-?12|high\s*school|teens?)\b", "Grades 9-12"),
    # Adults
    (r"\b(adults?\s*18\+|adult\s+only)\b", "Adults 18+"),
    # All ages
    (r"\ball\s*ages\b", "All Ages"),
]

def detect_ages(name: str, description: str, categories: List[str]) -> List[str]:
    text = f"{name}\n{description}\n{', '.join(categories)}".lower()
    hits = []
    for pattern, label in AGE_RULES:
        if re.search(pattern, text):
            hits.append(label)
    # Deduplicate while preserving order
    seen = set()
    ordered = []
    for x in hits:
        if x not in seen:
            ordered.append(x)
            seen.add(x)
    return ordered

# -----------------------------------------------------------------------------
# Fetch & merge feeds
# -----------------------------------------------------------------------------

def build_ics_url(audience: str, start_unix: int, end_unix: int) -> str:
    params = [
        ("filterBy[startsAt]", str(start_unix)),
        ("filterBy[endsAt]", str(end_unix)),
        ("pinnedFilters[0]", audience),  # server-side attempt
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
                # Union categories and ages
                old = merged[uid]
                old_cats = set(old.get("_categories", []))
                new_cats = set(e.get("_categories", []))
                old["_categories"] = list(old_cats.union(new_cats))
                old_ages = set(old.get("_ages", []))
                new_ages = set(e.get("_ages", []))
                old["_ages"] = list(old_ages.union(new_ages))
            else:
                merged[uid] = e
    return list(merged.values())

# -----------------------------------------------------------------------------
# Main scrape logic
# -----------------------------------------------------------------------------

def _event_dict_from_vevent(evt: Dict[str, str], audience_hint: str) -> Dict:
    name = (evt.get("SUMMARY") or "").strip()
    desc = (evt.get("DESCRIPTION") or "").strip()
    dtstart = (evt.get("DTSTART") or "").strip()
    dtend = (evt.get("DTEND") or "").strip()
    location = (evt.get("LOCATION") or "").strip()
    url = _extract_url(evt).strip()
    cats = _split_categories(evt)
    # Age detection from actual content; don't rely on audience hint for Ages
    ages = detect_ages(name, desc, cats)

    # If nothing detected, mark as Family (per request)
    categories = set([ "Event Location - Hampton" ])  # always-on
    if not ages:
        categories.add("Audience - Family Event")

    # Build sheet fields
    month, day, year = _fmt_date_parts(dtstart)
    time_str = _fmt_time_range(dtstart, dtend)

    return {
        # Internal fields for merge/logic
        "UID": evt.get("UID", "").strip(),
        "_url": url,
        "_categories": list(categories.union(set(cats))),
        "_ages": ages,

        # Sheet-facing fields (align with your uploader)
        "Event Link": url,
        "Name": name,                       # uploader will append (Hampton)
        "Description": desc,
        "Event Status": "Available",
        "Event Time": time_str,
        "Ages": ", ".join(ages) if ages else "",
        "Location": location,
        "Month": month,
        "Day": day,
        "Year": year,
        # Optional extras your pipeline may consume
        "Categories": ", ".join(sorted(categories.union(set(cats)))) if (categories or cats) else "",
        "Program Type": "",
        "Library": LIBRARY_KEY,
    }

def scrape_visithampton_hmva_ical(mode: str = "full") -> List[Dict]:
    """
    mode: 'full' (12 weeks) or 'fast' (4 weeks)
    Returns list of event dicts ready for upload_to_sheets.
    """
    weeks = 12 if mode == "full" else 4
    start_unix, end_unix = _time_window(weeks)

    all_lists: List[List[Dict]] = []
    for audience in AUDIENCE_FILTERS:
        url = build_ics_url(audience, start_unix, end_unix)
        ics_text = fetch_ics(url)
        vevents = _parse_vevent_blocks(ics_text)
        events_for_audience = []
        for v in vevents:
            # Convert each VEVENT to our dict; audience_hint is not used to force Ages
            ed = _event_dict_from_vevent(v, audience_hint=audience)
            events_for_audience.append(ed)
        all_lists.append(events_for_audience)

    merged = merge_events_by_uid(all_lists)

    # Final tidy: strip emojis (common in With feeds), trim fields
    def _strip_emojis(s: str) -> str:
        if not s:
            return s
        # Simple BMP filter; if you have a shared util, prefer it
        return re.sub(r"[\U00010000-\U0010FFFF]", "", s)
    for e in merged:
        for k in ("Name","Description","Location","Event Time","Ages","Categories"):
            e[k] = _strip_emojis(e.get(k, "")).strip()

    return merged

# -----------------------------------------------------------------------------
# Optional: auto-upload if your uploader is available
# -----------------------------------------------------------------------------

def _maybe_upload(rows: List[Dict], mode: str):
    try:
        # Expect your existing uploader with a function named `upload_events_to_sheet`
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
        # Still helpful to show a sample
        print(f"Prepared {len(rows)} rows locally.")

# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape VisitHampton (With iCal)")
    parser.add_argument("--mode", choices=["full","fast"], default="full",
                        help="full = next 12 weeks, fast = next 4 weeks")
    args = parser.parse_args()
    rows = scrape_visithampton_hmva_ical(mode=args.mode)
    _maybe_upload(rows, mode=args.mode)
