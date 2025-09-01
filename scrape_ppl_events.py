from datetime import datetime, timedelta, timezone
import requests
from ics import Calendar
from bs4 import BeautifulSoup
from constants import LIBRARY_CONSTANTS, TITLE_KEYWORD_TO_CATEGORY
import re
from zoneinfo import ZoneInfo
from constants import UNWANTED_TITLE_KEYWORDS


eastern = ZoneInfo("America/New_York")
ICAL_URL = "https://www.portsmouthpubliclibrary.org/common/modules/iCalendar/iCalendar.aspx?catID=24&feed=calendar"

def is_likely_adult_event(text):
    text = text.lower()
    keywords = [
        "adult", "18+", "21+", "resume", "job help", "tax help",
        "medicare", "investment", "retirement", "social security",
        "veterans", "finance", "knitting", "real estate"
    ]
    return any(kw in text for kw in keywords)

def extract_ages(text):
    text = text.lower()
    matches = set()

    # Range detection: ages 4-11, ages 5 – 12
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

    # "Under X" pattern
    under_match = re.search(r"(under|younger than)\s*(\d{1,2})", text)
    if under_match:
        age = int(under_match.group(2))
        if age <= 3:
            matches.add("Infant")
        elif age <= 5:
            matches.add("Preschool")
        else:
            matches.add("School Age")

    # Keyword detection
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

def is_cancelled(name, description):
    return "cancelled" in name.lower() or "canceled" in description.lower()

def scrape_ppl_events(mode="all"):
    print("\U0001F4DA Scraping Portsmouth Public Library events from iCal feed...")

    today = datetime.now(timezone.utc)
    if mode == "weekly":
        date_range_end = today + timedelta(days=7)
    elif mode == "monthly":
        date_range_end = today + timedelta(days=30)
    else:
        date_range_end = today + timedelta(days=90)

    resp = requests.get(ICAL_URL)
    calendar = Calendar(resp.text)
    ppl_constants = LIBRARY_CONSTANTS.get("ppl", {})
    name_suffix_map = ppl_constants.get("name_suffix_map", {})
    venue_map = ppl_constants.get("venue_names", {})
    age_to_categories = ppl_constants.get("age_to_categories", {})

    DEFAULT_CATEGORIES = "Audience - Family Event, Audience - Free Event, Audience - Preschool Age, Audience - School Age, Event Location - Portsmouth"

    events = []
    for event in calendar.events:
        try:
            if event.begin is None:
                continue

            event_date = event.begin.datetime.astimezone(eastern)
            if event_date < today or event_date > date_range_end:
                continue

            name = event.name.strip() if event.name else ""
            description = event.description.strip() if event.description else ""
            # 🚫 Skip unwanted titles
            if any(bad_word in name.lower() for bad_word in UNWANTED_TITLE_KEYWORDS):
                print(f"⏭️ Skipping: Unwanted title match → {name}")
                continue

            if is_likely_adult_event(name) or is_likely_adult_event(description):
                print(f"⏭️ Skipping: Adult event → {name}")
                continue

            event_link = None
            match = re.search(r"https://www\.portsmouthpubliclibrary\.org/calendar\.aspx\?EID=\d+", description)
            if match:
                event_link = match.group(0)
            else:
                continue  # skip malformed events

            # Clean up raw location
            raw_location = BeautifulSoup(event.location or "", "html.parser").get_text().strip()
            
            # First, try a full match from the map
            location = venue_map.get(raw_location)
            
            # If no exact match, try partial matching by searching keys
            if not location:
                normalized = raw_location.lower()
                for key, mapped in venue_map.items():
                    if key.lower() in normalized:
                        location = mapped
                        break
            
            # Fallback to raw if still not matched
            if not location:
                print(f"📌 Unmapped location: {repr(raw_location)}")
                location = raw_location

            start_dt = event.begin.datetime.astimezone(eastern)
            end_dt = event.end.datetime.astimezone(eastern) if event.end else start_dt + timedelta(hours=1)

            start_time = start_dt.strftime("%-I:%M %p")
            end_time = end_dt.strftime("%-I:%M %p")
            time_str = f"{start_time} - {end_time}" if end_time else start_time

            ages = extract_ages(name + " " + description)

            # Title-based category tagging
            base_cats = []
            combined_text = (name + " " + description).lower()
            for keyword, cat in TITLE_KEYWORD_TO_CATEGORY.items():
                if keyword in combined_text:
                    base_cats.extend([c.strip() for c in cat.split(",")])

            # Age-based category tagging
            age_tags = []
            for a in [a.strip() for a in ages.split(",") if a.strip()]:
                cat = age_to_categories.get(a)
                if cat:
                    age_tags.extend([c.strip() for c in cat.split(",")])

            # Clean and deduplicate tags
            # Clean and deduplicate tags
            all_tags = [c.strip() for c in base_cats + age_tags if c.strip()]
            
            # ✅ Always include these base tags
            all_tags.extend(["Audience - Free Event", "Event Location - Portsmouth"])
            
            # Deduplicate
            categories = ", ".join(dict.fromkeys(all_tags))

            # Fallback if still empty
            if not categories:
                categories = DEFAULT_CATEGORIES
            print(f"📌 Final categories for {name}: {categories}")
            events.append({
                "Event Name": name,
                "Event Link": event_link,
                "Event Status": "Cancelled" if is_cancelled(name, description) else "Available",
                "Time": time_str,
                "Ages": ages,
                "Location": location,
                "Month": event_date.strftime("%b"),
                "Day": str(event_date.day),
                "Year": str(event_date.year),
                "Event Date": event_date.strftime("%Y-%m-%d"),
                "Event End Date": end_dt.strftime("%Y-%m-%d"),
                "Event Description": description,
                "Series": "",
                "Program Type": "",
                "Categories": categories
            })
        except Exception as e:
            print(f"⚠️ Error parsing event: {e}")

    print(f"✅ Scraped {len(events)} events from Portsmouth Public Library.")
    return events
