# scrape_ppl_events.py
from datetime import datetime, timedelta, timezone
import re
import requests
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo
from urllib.parse import urljoin

from constants import (
    LIBRARY_CONSTANTS,
    TITLE_KEYWORD_TO_CATEGORY,
    UNWANTED_TITLE_KEYWORDS,
)

eastern = ZoneInfo("America/New_York")

BASE = "https://www.portsmouthpubliclibrary.org"
# Category/Calendar ID: taken from your ICS catID=24; CivicPlus list pages usually use CID
CATEGORY_ID = 24

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.8",
}

# -------------------------
# Helpers
# -------------------------

def is_likely_adult_event(text: str) -> bool:
    t = (text or "").lower()
    keywords = [
        "adult", "18+", "21+", "resume", "job help", "tax help",
        "medicare", "investment", "retirement", "social security",
        "veterans", "finance", "knitting", "real estate"
    ]
    return any(kw in t for kw in keywords)

def extract_ages(text: str) -> str:
    """Lightweight age bucket extraction (same intent as your ICS version)."""
    text = (text or "").lower()
    matches = set()

    # Range detection: ages 4–11, ages 5 – 12
    range_match = re.search(r"ages?\s*(\d{1,2})\s*[-–to]+\s*(\d{1,2})", text)
    if range_match:
        low = int(range_match.group(1))
        high = int(range_match.group(2))
        if high <= 3:
            matches.add("Infant")
        elif high <= 5:
            matches.add("Preschool")
        elif high <= 12:
            matches.add("School Age")
        elif high <= 17:
            matches.add("Teens")
        else:
            matches.add("Adults 18+")

    under_match = re.search(r"(under|younger than)\s*(\d{1,2})", text)
    if under_match:
        age = int(under_match.group(2))
        if age <= 3:
            matches.add("Infant")
        elif age <= 5:
            matches.add("Preschool")
        else:
            matches.add("School Age")

    if any(kw in text for kw in ["infants", "babies", "baby", "0-2"]):
        matches.add("Infant")
    if any(kw in text for kw in ["toddlers", "2-3", "2 and 3", "age 2", "age 3", "preschool"]):
        matches.add("Preschool")
    if any(kw in text for kw in ["school age", "elementary", "5-8", "ages 5", "grade"]):
        matches.add("School Age")
    if any(kw in text for kw in ["tween", "tweens", "middle school"]):
        matches.add("Tweens")
    if any(kw in text for kw in ["teen", "teens", "high school"]):
        matches.add("Teens")
    if "all ages" in text:
        matches.add("All Ages")

    return ", ".join(sorted(matches))

def is_cancelled(name: str, description: str) -> bool:
    t1 = (name or "").lower()
    t2 = (description or "").lower()
    return ("cancelled" in t1) or ("canceled" in t1) or ("cancelled" in t2) or ("canceled" in t2)

def _candidate_month_urls(year: int, month: int) -> list[str]:
    """
    Try several CivicPlus variants. The plain category URL is a reliable
    fallback (it shows the current month). Others may or may not work
    depending on site config.
    """
    return [
        # ✅ reliable: current month for the category (works on Portsmouth)
        f"{BASE}/calendar.aspx?CID={CATEGORY_ID}",
        # Attempt explicit month/year (some CivicPlus configs respect these):
        f"{BASE}/calendar.aspx?CID={CATEGORY_ID}&curm={month}&cury={year}",
        f"{BASE}/calendar.aspx?CID={CATEGORY_ID}&month={month}&year={year}",
        # Some sites use a trailing comma in CID to denote a list of calendars:
        f"{BASE}/calendar.aspx?CID={CATEGORY_ID}%2C&curm={month}&cury={year}",
        f"{BASE}/calendar.aspx?CID={CATEGORY_ID}%2C&month={month}&year={year}",
        # Date-range form params (works on some CivicPlus builds):
        f"{BASE}/calendar.aspx?CID={CATEGORY_ID}&startDate={month}%2F1%2F{year}",
    ]

def _fetch_month_event_links(year: int, month: int) -> list[str]:
    links = set()
    for url in _candidate_month_urls(year, month):
        try:
            headers = dict(HEADERS)
            headers["Referer"] = f"{BASE}/calendar.aspx"
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code >= 400:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")

            # find any anchor that contains ?EID= (case-insensitive)
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "calendar.aspx?eid=" in href.lower():
                    links.add(urljoin(BASE, href))
            if links:
                return sorted(links)
        except Exception:
            continue
    return sorted(links)


def _parse_event_detail(url: str) -> dict:
    """
    Parse a CivicPlus event detail page and extract:
    title, date (YYYY-MM-DD), start/end times (if found), location, description.
    We use several heuristics to tolerate template differences.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception:
        return {}

    # Title
    title = ""
    for sel in ["h1", "h2", ".itemTitle", "#lblEventName"]:
        el = soup.select_one(sel)
        if el:
            title = el.get_text(strip=True)
            break

    # Description (try common containers; fallback to main content)
    desc_selectors = [
        ".Description, #EventDescription, #EventBody, .eventDetailDescription, .cp-event-description",
        ".page-content, #divMain, #content, .content, .main-content",
    ]
    description = ""
    for selector in desc_selectors:
        el = soup.select_one(selector)
        if el:
            description = el.get_text(" ", strip=True)
            if len(description) >= 10:
                break
    if not description:
        description = soup.get_text(" ", strip=True)

    # Location: look for label 'Location' nearby or a known field
    location = ""
    # CivicPlus often has dl/dt/dd pairs with labels
    for row in soup.select("dl, .cp-details, .detail_list"):
        text = row.get_text(" ", strip=True)
        m = re.search(r"Location\s*:?\s*(.+)", text, re.IGNORECASE)
        if m:
            # stop at next label if present
            loc = m.group(1)
            loc = re.split(r"\b(Date|Time|Cost|Contact|Phone|Email)\b\s*:?", loc, 1, flags=re.IGNORECASE)[0]
            location = loc.strip()
            break
    # fallback simple search
    if not location:
        text = soup.get_text(" ", strip=True)
        m = re.search(r"Location\s*:?\s*(.+?)\s{2,}", text, re.IGNORECASE)
        if m:
            location = m.group(1).strip()

    # Date: first try structured patterns (e.g., "Monday, September 9, 2025")
    full_text = soup.get_text(" ", strip=True)
    date_obj = None
    date_match = re.search(
        r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})",
        full_text, re.IGNORECASE
    )
    if date_match:
        month_name = date_match.group(2)
        day = int(date_match.group(3))
        year = int(date_match.group(4))
        try:
            date_obj = datetime.strptime(f"{month_name} {day} {year}", "%B %d %Y").replace(tzinfo=eastern)
        except Exception:
            date_obj = None

    # Time: try to find a range "H:MM AM - H:MM PM" or single time
    start_time, end_time = "", ""
    time_match = re.search(
        r"(\d{1,2}:\d{2}\s*[AP]M)\s*[-–—]\s*(\d{1,2}:\d{2}\s*[AP]M)",
        full_text, re.IGNORECASE
    )
    if time_match:
        start_time = _fmt_time12(_parse_time12(time_match.group(1)))
        end_time = _fmt_time12(_parse_time12(time_match.group(2)))
    else:
        # look for "Time: 10:00 AM" or "at 2:00 PM"
        one_time = re.search(r"(?:Time\s*:?\s*|at\s+)(\d{1,2}:\d{2}\s*[AP]M)", full_text, re.IGNORECASE)
        if one_time:
            start_time = _fmt_time12(_parse_time12(one_time.group(1)))

    return {
        "title": title,
        "description": description,
        "location": location,
        "date_obj": date_obj,  # datetime in America/New_York (or None)
        "start_time": start_time,
        "end_time": end_time,
    }

def _parse_time12(t: str):
    t = (t or "").upper().replace(".", "").strip()
    for fmt in ("%I:%M %p", "%I %p"):
        try:
            return datetime.strptime(t, fmt)
        except ValueError:
            continue
    return None

def _fmt_time12(dt: datetime | None) -> str:
    if not dt:
        return ""
    # Keep minutes only if present in original pattern (best-effort)
    return dt.strftime("%-I:%M %p")

def _dedupe_keep_order(items):
    seen, out = set(), []
    for x in items:
        if x and x not in seen:
            out.append(x)
            seen.add(x)
    return out

# -------------------------
# Main scrape
# -------------------------

def scrape_ppl_events(mode="all"):
    print("📚 Scraping Portsmouth Public Library (HTML month iterator)…")

    today = datetime.now(timezone.utc).astimezone(eastern).replace(hour=0, minute=0, second=0, microsecond=0)
    if mode == "weekly":
        end_cutoff = today + timedelta(days=7)
    elif mode == "monthly":
        end_cutoff = today + timedelta(days=30)
    else:
        end_cutoff = today + timedelta(days=90)

    # months to fetch: current + next
    this_month = today.month
    this_year = today.year
    next_dt = (today + timedelta(days=32))
    next_month = next_dt.month
    next_year = next_dt.year

    month_links = []
    for (y, m) in [(this_year, this_month), (next_year, next_month)]:
        links = _fetch_month_event_links(y, m)
        print(f"🗓 Found {len(links)} event links for {y}-{m:02d}")
        month_links.extend(links)

    # De-dupe detail links
    detail_links = _dedupe_keep_order(month_links)

    ppl_constants = LIBRARY_CONSTANTS.get("ppl", {})
    venue_map = ppl_constants.get("venue_names", {}) or {}
    age_to_categories = ppl_constants.get("age_to_categories", {}) or {}

    DEFAULT_CATEGORIES = (
        "Audience - Family Event, Audience - Free Event, "
        "Audience - Preschool Age, Audience - School Age, Event Location - Portsmouth"
    )

    events = []
    for link in detail_links:
        try:
            # Detail parse
            data = _parse_event_detail(link)
            if not data:
                continue

            name = data["title"].strip()
            description = (data["description"] or "").strip()
            raw_location = (data["location"] or "").strip()
            event_date_obj = data["date_obj"]

            # If date wasn't found in detail, skip (we need date to filter window)
            if not event_date_obj:
                # last resort: try to infer from URL fragment like ".../EventDate=9/10/2025"
                m = re.search(r"(EventDate|day|date)=(\d{1,2})/(\d{1,2})/(\d{4})", link, re.IGNORECASE)
                if m:
                    month = int(m.group(2)); day = int(m.group(3)); year = int(m.group(4))
                    try:
                        event_date_obj = datetime(year, month, day, tzinfo=eastern)
                    except Exception:
                        pass
            if not event_date_obj:
                continue

            # Apply date window: today → end_cutoff
            if event_date_obj < today or event_date_obj > end_cutoff:
                continue

            # 🚫 Skip unwanted titles
            if any(bad_word in name.lower() for bad_word in UNWANTED_TITLE_KEYWORDS):
                print(f"⏭️ Skipping (unwanted title): {name}")
                continue

            # Skip likely adult events
            if is_likely_adult_event(name) or is_likely_adult_event(description):
                print(f"⏭️ Skipping (adult): {name}")
                continue

            # Normalize location
            location = venue_map.get(raw_location, raw_location)
            if not location:
                location = "Portsmouth Main Library"  # gentle fallback

            start_time = data["start_time"]
            end_time = data["end_time"]
            time_str = f"{start_time} - {end_time}" if start_time and end_time else (start_time or "")

            ages = extract_ages(name + " " + description)

            # Title keyword tags
            base_cats = []
            combined_text = (name + " " + description).lower()
            for keyword, cat in TITLE_KEYWORD_TO_CATEGORY.items():
                if keyword in combined_text:
                    base_cats.extend([c.strip() for c in cat.split(",")])

            # Age mapping tags
            age_tags = []
            for a in [a.strip() for a in (ages or "").split(",") if a.strip()]:
                cat = age_to_categories.get(a)
                if cat:
                    age_tags.extend([c.strip() for c in cat.split(",")])

            # Always add these for PPL
            all_tags = [c.strip() for c in base_cats + age_tags if c.strip()]
            all_tags.extend(["Audience - Free Event", "Event Location - Portsmouth"])
            categories = ", ".join(dict.fromkeys(all_tags)) or DEFAULT_CATEGORIES

            events.append({
                "Event Name": name,
                "Event Link": link,
                "Event Status": "Cancelled" if is_cancelled(name, description) else "Available",
                "Time": time_str,
                "Ages": ages,
                "Location": location,
                "Month": event_date_obj.strftime("%b"),
                "Day": str(event_date_obj.day),
                "Year": str(event_date_obj.year),
                "Event Date": event_date_obj.strftime("%Y-%m-%d"),
                "Event End Date": event_date_obj.strftime("%Y-%m-%d"),
                "Event Description": description,
                "Series": "",
                "Program Type": "",
                "Categories": categories
            })

        except Exception as e:
            print(f"⚠️ Error parsing detail: {link} → {e}")

    print(f"✅ Scraped {len(events)} events from PPL (HTML).")
    return events
