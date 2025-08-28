# scrap_visitnorfolk_events.py

from datetime import datetime, timedelta, timezone
import requests, re, html
from ics import Calendar
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo
from constants import TITLE_KEYWORD_TO_CATEGORY

EASTERN = ZoneInfo("America/New_York")

ICAL_URLS = [
    "https://www.norfolk.gov/common/modules/iCalendar/iCalendar.aspx?catID=24&feed=calendar",
    "https://www.norfolk.gov/common/modules/iCalendar/iCalendar.aspx?catID=73&feed=calendar",
    "https://www.norfolk.gov/common/modules/iCalendar/iCalendar.aspx?catID=75&feed=calendar",
    "https://www.norfolk.gov/common/modules/iCalendar/iCalendar.aspx?catID=145&feed=calendar",
]

# Prefer canonical event links like: https://www.norfolk.gov/calendar.aspx?EID=14902
EID_LINK_RE = re.compile(r"https://www\.norfolk\.gov/calendar\.aspx\?EID=\d+")
# Some LOCATION values include HTML like <p>Venue</p> - 123 St
TAG_RE = re.compile(r"<[^>]+>")

ALWAYS_ON_CATEGORIES = [
    "Event Location - Norfolk",
    "Event Location - Family Event",  # per your request (note: your other scrapers typically use "Audience - Family Event")
]

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
    return (dt
