# scrap_visitnorfolk_events.py

from datetime import datetime, timedelta, timezone
import requests, re, html
from ics import Calendar
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo
from constants import TITLE_KEYWORD_TO_CATEGORY
from constants import LIBRARY_CONSTANTS
from constants import UNWANTED_TITLE_KEYWORDS


EASTERN = ZoneInfo("America/New_York")

UNWANTED_LOCATIONS = {
    "endtime united church of jesus",
    "pretlow branch library",
}

ICAL_URLS = [
    "https://www.norfolk.gov/common/modules/iCalendar/iCalendar.aspx?catID=24&feed=calendar",
    "https://www.norfolk.gov/common/modules/iCalendar/iCalendar.aspx?catID=152&feed=calendar",
    "https://www.norfolk.gov/common/modules/iCalendar/iCalendar.aspx?catID=75&feed=calendar",
    "https://www.norfolk.gov/common/modules/iCalendar/iCalendar.aspx?catID=145&feed=calendar",
]

# Prefer canonical event links like: https://www.norfolk.gov/calendar.aspx?EID=14902
EID_LINK_RE = re.compile(r"https://www\.norfolk\.gov/calendar\.aspx\?EID=\d+")
# Some LOCATION values include HTML like <p>Venue</p> - 123 St
TAG_RE = re.compile(r"<[^>]+>")

ALWAYS_ON_CATEGORIES = [
    "Event Location - Norfolk",
    "Audience - Family Event", 
]

# Put near the top with the other regexes/utilities
ADDR_SPLIT_RE = re.compile(r"\s[-–]\s")   # "Venue - 123 St" or "Venue – 123 St"

def _strip_address(loc: str) -> str:
    """
    Keep just the venue name:
    - If there's a " - " or " – " separator, take the left side.
    - Otherwise, if there's a street number (space + 2–5 digits), cut before it.
      (Prevents chopping names like 'Studio 54' which have digits but not as an address.)
    """
    s = _clean_text(loc)
    # Case 1: split on hyphen/en dash separators
    parts = ADDR_SPLIT_RE.split(s, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip()

    # Case 2: trim when an address number appears after a space (e.g., "Venue 4320 Hampton Blvd")
    m = re.search(r"\s\d{2,5}\b", s)
    if m:
        return s[:m.start()].rstrip()

    return s

def _clean_text(s: str) -> str:
    if not s:
        return ""
    s = html.unescape(s)
    s = TAG_RE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _fmt_time_range(start_dt, end_dt):
    """Return 'H:MM AM - H:MM PM'. If end missing or == start, synthesize +60m."""
    if not start_dt:
        return ""
    s_local = start_dt.astimezone(EASTERN)
    if end_dt:
        e_local = end_dt.astimezone(EASTERN)
        if e_local == s_local:
            e_local = s_local + timedelta(hours=1)
    else:
        e_local = s_local + timedelta(hours=1)
    s = s_local.strftime("%-I:%M %p")
    e = e_local.strftime("%-I:%M %p")
    return f"{s} - {e}"

def _infer_ages(text: str) -> str:
    """Infer age buckets from title+description."""
    t = (text or "").lower()
    buckets = set()

    # explicit ranges like "ages 6-11" or "ages 6 to 11"
    m = re.search(r"ages?\s*(\d{1,2})\s*(?:[-–to]+)\s*(\d{1,2})", t)
    if m:
        low, high = int(m.group(1)), int(m.group(2))
        if high <= 3: buckets.add("Infant")
        elif high <= 5: buckets.add("Preschool")
        elif high <= 12: buckets.add("School Age")
        elif high <= 17: buckets.add("Teens")
        else: buckets.add("Adults 18+")

    # "under X" / "X and under"
    m = re.search(r"(?:under|younger than|and under)\s*(\d{1,2})", t)
    if m:
        age = int(m.group(1))
        if age <= 3: buckets.add("Infant")
        elif age <= 5: buckets.add("Preschool")
        else: buckets.add("School Age")

    # grade ranges (e.g., grades 3-5)
    gm = re.search(r"grades?\s*(\d{1,2})(?:\s*[-–to]+\s*(\d{1,2}))?", t)
    if gm:
        start_g = int(gm.group(1))
        end_g = int(gm.group(2)) if gm.group(2) else start_g
        if end_g <= 5: buckets.add("School Age")
        else: buckets.add("Teens")

    # keyword-based signals
    if any(k in t for k in ["infants", "babies", "baby", "0-2"]): buckets.add("Infant")
    if any(k in t for k in ["toddlers", "toddler", "preschool", "3-5", "ages 3-5", "2-3", "age 2", "age 3"]): buckets.add("Preschool")
    if any(k in t for k in ["school age", "elementary", "grade", "5-8", "ages 5"]): buckets.add("School Age")
    if any(k in t for k in ["tween", "tweens", "middle school"]): buckets.add("Tweens")
    if any(k in t for k in ["teen", "teens", "high school", "young adult"]): buckets.add("Teens")
    if "all ages" in t: buckets.add("All Ages")

    # Return sorted, comma-separated
    return ", ".join(sorted(buckets))

def _age_to_categories(ages_str: str):
    """Map inferred age buckets to category tags (Norfolk-specific)."""
    age_map = {
        "Infant":       "Audience - Toddler/Infant, Audience - Free Event, Event Location - Norfolk",
        "Preschool":    "Audience - Preschool Age, Audience - Free Event, Audience - Parent & Me, Event Location - Norfolk",
        "School Age":   "Audience - School Age, Audience - Free Event, Event Location - Norfolk",
        "Tweens":       "Audience - School Age, Audience - Free Event, Event Location - Norfolk",
        "Teens":        "Audience - Teens, Audience - Free Event, Event Location - Norfolk",
        "All Ages":     "Audience - Free Event, Event Location - Norfolk",
        "Adults 18+":   "Audience - Free Event, Event Location - Norfolk",
    }
    out = []
    for a in [x.strip() for x in (ages_str or "").split(",") if x.strip()]:
        if a in age_map:
            out.extend([c.strip() for c in age_map[a].split(",")])
    return out

def _keyword_categories(title: str, desc: str):
    """Map keywords to categories using constants.TITLE_KEYWORD_TO_CATEGORY."""
    txt = f"{title} {desc}".lower()
    tags = []
    for kw, cat in TITLE_KEYWORD_TO_CATEGORY.items():
        if kw in txt:
            tags.extend([c.strip() for c in cat.split(",")])
    return tags

def _dedupe_preserve_order(items):
    seen, out = set(), []
    for x in items:
        if x and x not in seen:
            out.append(x); seen.add(x)
    return out

def _is_cancelled(name: str, desc: str) -> bool:
    t = f"{name} {desc}".lower()
    return ("canceled" in t) or ("cancelled" in t)

def _canonical_link(description: str, uid: str) -> str:
    m = EID_LINK_RE.search(description or "")
    if m:
        return m.group(0)
    # Fallback: build from numeric UID if present
    if uid and uid.isdigit():
        return f"https://www.norfolk.gov/calendar.aspx?EID={uid}"
    # Last resort: empty string (will be skipped by uploader if missing)
    return ""

def _within_range(dt_utc: datetime, start: datetime, end: datetime) -> bool:
    return (dt_utc >= start) and (dt_utc <= end)

def scrap_visitnorfolk_events(mode="all"):
    """
    Scrape VisitNorfolk iCal feeds and return normalized events.
    Returns a list of dicts ready for upload_to_sheets.py.
    """
    print("🗓️  Scraping VisitNorfolk iCal feeds…")

    today_utc = datetime.now(timezone.utc)
    if mode == "weekly":
        date_start = today_utc
        date_end   = today_utc + timedelta(days=7)
    elif mode == "monthly":
        date_start = today_utc
        date_end   = today_utc + timedelta(days=30)   # rolling 30 days
    else:
        date_start = today_utc
        date_end   = today_utc + timedelta(days=90)



    events = []
    seen_links = set()

    for url in ICAL_URLS:
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            cal = Calendar(resp.text)

            for ev in cal.events:
                try:
                    if not ev.begin:
                        continue

                    # Normalize datetimes to UTC for range filtering
                    start_dt = ev.begin.datetime
                    end_dt   = ev.end.datetime if ev.end else None
                    if not isinstance(start_dt, datetime):
                        continue
                    
                    # guard against tz-naive (rare, but safe)
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=EASTERN)
                    
                    start_utc = start_dt.astimezone(timezone.utc)
                    if not (date_start <= start_utc <= date_end):
                        continue
                        
                    title = _clean_text(getattr(ev, "name", "") or "")
                    description = _clean_text(getattr(ev, "description", "") or "")
                    location = _clean_text(getattr(ev, "location", "") or "")
                    uid = _clean_text(getattr(ev, "uid", "") or "")

                    # 🚫 Skip unwanted title keywords
                    if any(bad_word.lower() in title.lower() for bad_word in UNWANTED_TITLE_KEYWORDS):
                        print(f"⏭️ Skipping (unwanted title match): {title}")
                        continue

                    # Normalize location against constants
                    vn_constants = LIBRARY_CONSTANTS.get("visitnorfolk", {})
                    venue_map = vn_constants.get("venue_names", {})
                    location = venue_map.get(location, location)
                    
                    # strip any appended address, then remove any leading stray hyphen
                    location = _strip_address(location)
                    location = re.sub(r"^\s*-\s*", "", location)

                    # 🚫 Skip events at unwanted locations
                    if any(bad in location.lower() for bad in UNWANTED_LOCATIONS):
                        print(f"⏭️ Skipping (unwanted location): {title} @ {location}")
                        continue

                    # Build canonical link
                    link = _canonical_link(description, uid)
                    if not link:
                        # If we truly can't get a canonical link, skip (uploader expects a link key)
                        print(f"⏭️  Skipping (no link): {title}")
                        continue

                    if link in seen_links:
                        continue
                    seen_links.add(link)

                    # Time & date parts
                    time_str = _fmt_time_range(start_dt, end_dt)
                    start_local = start_dt.astimezone(EASTERN)
                    end_local = (end_dt.astimezone(EASTERN) if end_dt else start_local + timedelta(hours=1))

                    month = start_local.strftime("%b")
                    day = str(start_local.day)
                    year = str(start_local.year)

                    # Ages + categories
                    ages = _infer_ages(f"{title} {description}")
                    keyword_tags = _keyword_categories(title, description)
                    age_tags = _age_to_categories(ages)
                    base_tags = ALWAYS_ON_CATEGORIES[:]  # copy

                    all_tags = _dedupe_preserve_order(base_tags + keyword_tags + age_tags)

                    events.append({
                        "Event Name": title,
                        "Event Link": link,
                        "Event Status": "Cancelled" if _is_cancelled(title, description) else "Available",
                        "Time": time_str,
                        "Ages": ages,                           # keep raw inferred ages; uploader augments categories too
                        "Location": location,
                        "Month": month,
                        "Day": day,
                        "Year": year,
                        "Event Date": start_local.strftime("%Y-%m-%d"),
                        "Event End Date": end_local.strftime("%Y-%m-%d"),
                        "Event Description": description,
                        "Series": "",
                        "Program Type": "",
                        "Categories": ", ".join(all_tags),
                    })
                except Exception as e:
                    print(f"⚠️  Error parsing event in {url}: {e}")
        except Exception as e:
            print(f"❌ Failed to fetch iCal: {url} — {e}")

    print(f"✅ Scraped {len(events)} VisitNorfolk events.")
    return events

if __name__ == "__main__":
    # Quick local test
    out = scrap_visitnorfolk_events(mode="weekly")
    print(f"Sample: {out[0] if out else 'NO EVENTS'}")
