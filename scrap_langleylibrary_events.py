import requests, re
from bs4 import BeautifulSoup
from helpers import rJson, wJson
from datetime import datetime, timedelta, timezone
from constants import TITLE_KEYWORD_TO_CATEGORY
from constants import UNWANTED_TITLE_KEYWORDS

BASE_URL = "https://www.langleylibrary.org/teen-events"
BASE_URL2 = "https://www.langleylibrary.org/kids-events"
ALWAYS_ON_CATEGORIES = [
    "Event Location - Hampton",
    "Audience - Family Event",
    "Audience - Free Event",
    "Audience - Military Only"
]

def filter_and_sort_events(events, date_start, date_end):
    """
    Filter and sort events based on date range.

    Args:
        events (list[dict]): List of events, each must have "date" key as string "YYYY-MM-DD".
        date_start (datetime): Start date (inclusive).
        date_end (datetime): End date (inclusive).

    Returns:
        list[dict]: Filtered and sorted list of events.
    """
    # Convert string dates to datetime for filtering
    filtered_events = []
    for event in events:
        event_date = datetime.strptime(event["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if date_start <= event_date <= date_end:
            filtered_events.append(event)

    # Sort ascending by date string (or by datetime for safety)
    filtered_events.sort(key=lambda e: e["date"])
    return filtered_events

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
    """Map inferred age buckets to category tags (Bateman Library-specific)."""
    age_map = {
        "Infant":       "Audience - Toddler/Infant, Audience - Free Event, Event Location - Bateman Library",
        "Preschool":    "Audience - Preschool Age, Audience - Free Event, Audience - Parent & Me, Event Location - Bateman Library",
        "School Age":   "Audience - School Age, Audience - Free Event, Event Location - Bateman Library",
        "Tweens":       "Audience - School Age, Audience - Free Event, Event Location - Bateman Library",
        "Teens":        "Audience - Teens, Audience - Free Event, Event Location - Bateman Library",
        "All Ages":     "Audience - Free Event, Event Location - Bateman Library",
        "Adults 18+":   "Audience - Free Event, Event Location - Bateman Library",
    }
    out = []
    for a in [x.strip() for x in (ages_str or "").split(",") if x.strip()]:
        if a in age_map:
            out.extend([c.strip() for c in age_map[a].split(",")])
    return out

def _keyword_categories(title: str, desc: str, cats: str):
    """Map keywords to categories using constants.TITLE_KEYWORD_TO_CATEGORY."""
    txt = f"{title} {desc} {cats}".lower()
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

def get_events_data(soup: BeautifulSoup, url):

    events = []

    for article in soup.select("div.eventlist.eventlist--upcoming article.eventlist-event"):
        # Title
        title_tag = article.select_one(".eventlist-title a")
        title = title_tag.get_text(strip=True) if title_tag else None
        link = url + title_tag["href"] if title_tag else None

        # 🚫 Skip unwanted title keywords
        if any(bad_word.lower() in title.lower() for bad_word in UNWANTED_TITLE_KEYWORDS):
            print(f"⏭️ Skipping (unwanted title match): {title}")
            continue

        # Date
        date_tag = article.select_one("time.event-date")
        date_text = date_tag.get_text(strip=True) if date_tag else None
        date_iso = date_tag["datetime"] if date_tag else None

        try:
            dt = datetime.strptime(date_iso, "%Y-%m-%d")
            Month = dt.strftime("%b")   # e.g., "Aug"
            Day = str(dt.day)           # e.g., "11"
            Year = str(dt.year)         # e.g., "2025"
        except Exception:
            Month = Day = Year = ""

        # Start/End Time
        start_time = article.select_one("time.event-time-12hr-start")
        end_time = article.select_one("time.event-time-12hr-end")
        start_12hr = start_time.get_text(strip=True).replace(' ',' ') if start_time else None
        end_12hr = end_time.get_text(strip=True).replace(' ',' ') if end_time else None

        start_time_24 = article.select_one("time.event-time-24hr-start")
        end_time_24 = article.select_one("time.event-time-24hr-end")
        start_24hr = start_time_24.get_text(strip=True) if start_time_24 else None
        end_24hr = end_time_24.get_text(strip=True) if end_time_24 else None

        # Location
        location_tag = article.select_one(".eventlist-meta-address")
        location = location_tag.get_text(strip=True).replace("(map)","") if location_tag else None
        map_link = None
        if location_tag:
            map_link_tag = location_tag.select_one("a")
            map_link = map_link_tag["href"] if map_link_tag else None
            if map_link:
                address = map_link.split("?q=")[-1]

        # cats
        cats = [c.get_text(strip=True) for c in article.select(".eventlist-cats a")]

        # Description
        description_parts = [p.get_text(" ", strip=True) for p in article.select(".eventlist-excerpt p")]
        description = " ".join(description_parts).strip()

        # Image
        img_tag = article.select_one(".eventlist-column-thumbnail img")
        img_url = img_tag.get("data-src") if img_tag else None

        # Ages + categories
        ages = _infer_ages(f"{title} {description} {' '.join(cats)}")
        keyword_tags = _keyword_categories(title, description, ' '.join(cats))
        age_tags = _age_to_categories(ages)
        base_tags = ALWAYS_ON_CATEGORIES[:]  # copy

        all_tags = _dedupe_preserve_order(base_tags + keyword_tags + age_tags)


        events.append({
            "Event Name": title,
            "Event Link": link,
            "Event Description": description,
            "Categories": ", ".join(all_tags),
            "date": date_iso,
            "Month": Month,
            "Day": Day,
            "Year": Year,
            "Time": f"{start_12hr} - {end_12hr}",
            "Location": location,
            "address": address,
            "date_text": date_text,
            "start_time_12hr": start_12hr,
            "end_time_12hr": end_12hr,
            "start_time_24hr": start_24hr,
            "end_time_24hr": end_24hr,
            "map_link": map_link,
            "cats": cats,
            "image": img_url
        })

    return events

def fetch_events(url):

    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "en-US,en;q=0.9,ar-JO;q=0.8,ar;q=0.7,ja-JP;q=0.6,ja;q=0.5",
        # "if-none-match": 'W/"e2d4703cdadf9b01540f6f13cea41578"',
        "priority": "u=0, i",
        "sec-ch-ua": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    }

    # Send request
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # raise error if request failed
    

    # Parse HTML
    soup = BeautifulSoup(response.text, "html.parser")
    section_page = soup.find("section", id="page")

    return get_events_data(section_page, url)

def scrap_langleylibrary(mode="all"):
    """
    Scrape langleylibrary and return normalized events.
    Returns a list of dicts ready for upload_to_sheets.py.
    """
    print("🗓️  Scraping langleylibrary ...")

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

    events = fetch_events(BASE_URL)
    events2 = fetch_events(BASE_URL2)
    events.extend(events2)
    events = filter_and_sort_events(events, date_start, date_end)

    return events



if __name__ == "__main__":

    # wJson(scrap_langleylibrary(), "events.json")
    pass
