from datetime import datetime, timedelta, timezone
import requests
from ics import Calendar
from bs4 import BeautifulSoup
from constants import LIBRARY_CONSTANTS
import re
from constants import UNWANTED_TITLE_KEYWORDS
from constants import TITLE_KEYWORD_TO_CATEGORY

ICAL_URL = "https://www.hampton.gov/common/modules/iCalendar/iCalendar.aspx?catID=24&feed=calendar"

def is_likely_adult_event(text):
    text = text.lower()
    keywords = [
        "veteran support services",
        "workforce hampton",
        "all-comers writing club",
        "show and tell",
        "podcraft: seed sowing sessions",
        "legal aid",
        "human services",
        "documentary",
        "world war ii",
        "the joys of sourdough",
        "beginner computer class",
        "tech detectives",
        "computer class series",
        "adults", "adult", "21+", "18+",
        "genealogy", "book club", "knitting",
        "resume", "job search", "tax help",
        "investment", "social security", "medicare",
        "crafts for adults", "finance", "retirement",
        "blackout poetry"
    ]
    return any(kw in text for kw in keywords)

def scrape_hpl_events(mode="all"):
    print("📚 Scraping Hampton Public Library events from iCal feed...")

    today = datetime.now(timezone.utc)
    if mode == "weekly":
        date_range_end = today + timedelta(days=7)
    elif mode == "monthly":
        date_range_end = today + timedelta(days=30)
    else:
        date_range_end = today + timedelta(days=90)

    resp = requests.get(ICAL_URL)
    calendar = Calendar(resp.text)
    program_type_to_categories = LIBRARY_CONSTANTS["hpl"].get("program_type_to_categories", {})
    HPL_LOCATION_MAP = LIBRARY_CONSTANTS["hpl"].get("location_map", {})

    events = []
    for event in calendar.events:
        try:
            if event.begin is None:
                continue
            event_date = event.begin.datetime.astimezone(timezone.utc)
            if event_date > date_range_end:
                continue

            name = event.name.strip() if event.name else ""
            description = event.description.strip() if event.description else ""
            # Skip unwanted titles like "Summer Meals"
            if any(bad_word in name.lower() for bad_word in UNWANTED_TITLE_KEYWORDS):
                print(f"⏭️ Skipping: Unwanted title match → {name}")
                continue
            
            if is_likely_adult_event(name) or is_likely_adult_event(description):
                continue
            
            combined_text = f"{name} {description}".lower()
            
            program_categories = []
            program_type = ""
            for keyword, cat in program_type_to_categories.items():
                if re.search(rf"\b{re.escape(keyword.lower())}\b", combined_text):
                    program_type = keyword.capitalize()
                    program_categories.extend([c.strip() for c in cat.split(",")])
            
            keyword_tags = []
            for keyword, cat in TITLE_KEYWORD_TO_CATEGORY.items():
                if re.search(rf"\b{re.escape(keyword.lower())}\b", combined_text):
                    keyword_tags.extend([c.strip() for c in cat.split(",")])
            
            categories = ", ".join(dict.fromkeys(program_categories + keyword_tags))


            # Extract clean location
            # === LOCATION MAPPING ===
            raw_location_html = event.location or ""
            raw_location = BeautifulSoup(raw_location_html, "html.parser").get_text().strip()
            normalized = raw_location.lower()
            location = None
            for key, mapped in HPL_LOCATION_MAP.items():
                if key.lower() in normalized:
                    location = mapped
                    break
            if not location:
                print(f"📌 Unmapped location: {repr(raw_location)}")
                location = raw_location  # fallback so we still export it


            # Extract event link from description
            event_link = None
            if description:
                url_match = re.search(r"https://www\.hampton\.gov/calendar\.aspx\?EID=\d+", description)
                if url_match:
                    event_link = url_match.group(0)
            if not event_link:
                print(f"⚠️  Skipping malformed event (missing link): {name} @ {location}")
                continue

            # Format time
            start_time = event.begin.datetime.astimezone(timezone.utc).strftime("%-I:%M %p")
            end_time = event.end.datetime.astimezone(timezone.utc).strftime("%-I:%M %p") if event.end else ""
            time_str = f"{start_time} - {end_time}" if end_time else start_time

            events.append({
                "Event Name": name,
                "Event Link": event_link,
                "Event Status": "Available",
                "Time": time_str,
                "Ages": "",
                "Location": location,
                "Month": event_date.strftime("%b"),
                "Day": str(event_date.day),
                "Year": str(event_date.year),
                "Event Date": event_date.strftime("%Y-%m-%d"),
                "Event End Date": event.end.datetime.astimezone(timezone.utc).strftime("%Y-%m-%d") if event.end else event_date.strftime("%Y-%m-%d"),
                "Event Description": description,
                "Series": "",
                "Program Type": program_type,
                "Categories": categories
            })
        except Exception as e:
            print(f"⚠️ Error parsing event: {e}")

    print(f"✅ Scraped {len(events)} events from Hampton Public Library.")
    return events
