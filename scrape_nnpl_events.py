from datetime import datetime, timedelta, timezone
import requests
from ics import Calendar
from bs4 import BeautifulSoup
from constants import LIBRARY_CONSTANTS
import re
from zoneinfo import ZoneInfo
eastern = ZoneInfo("America/New_York")

ICAL_URL = "https://calendar.nnpl.org/api/feeds/ics/nnlibrary"

def is_likely_adult_event(text):
    text = text.lower()
    keywords = [
        "veteran support services",
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
        "meet up mondays",
        "computer essentials", "computer basics", "basic computer skills", "excel", "word", "photoshop",
        "blackout poetry"
    ]
    return any(kw in text for kw in keywords)

def extract_tags(text):
    matches = re.findall(r"\b(?:Event|[A-Z][a-z]+(?:[A-Z][a-z]+)*)\b", text)
    return ", ".join(set(matches)) if matches else ""

def extract_ages(text):
    text = text.lower()
    matches = set()

    # === Keyword-Based Detection ===
    if any(kw in text for kw in ["infants", "babies", "baby", "0-2"]):
        matches.add("Infant")
    if any(kw in text for kw in ["preschool", "toddlers", "age 2", "aged 2", "ages 2", "2-year-olds"]):
        matches.add("Preschool")
    if any(kw in text for kw in ["school age", "school-age", "children ages 5", "elementary"]):
        matches.add("School Age")
    if any(kw in text for kw in ["teen", "teens", "middle school", "high school"]):
        matches.add("Teens")
    if any(kw in text for kw in ["18+", "adults", "adult", "grown-ups"]):
        matches.add("Adults 18+")
        
    # === Specific phrasing detection ===
    if re.search(r"ages?\s*\d+\s*(through|to)\s*\d+", text):
        matches.add("Preschool")  # or logic to determine range if you want
    if "all ages" in text:
        matches.add("All Ages")
    if "children of all ages" in text:
        matches.add("Children")

    # === Range Detection: "ages 6–11" or "ages 6 to 11" ===
    range_match = re.search(r"ages?\s*(\d{1,2})\s*(?:[-–to]+)\s*(\d{1,2})", text)
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

    # === "under X" pattern: "children 5 and under" ===
    under_match = re.search(r"(?:under|younger than|and under)\s*(\d{1,2})", text)
    if under_match:
        age = int(under_match.group(1))
        if age <= 3:
            matches.add("Infant")
        elif age <= 5:
            matches.add("Preschool")
        else:
            matches.add("School Age")

    # === Grade Detection ===
    grade_match = re.search(r"grades?\s*(\d{1,2})(?:\s*[-–to]+\s*(\d{1,2}))?", text)
    if grade_match:
        start_grade = int(grade_match.group(1))
        end_grade = int(grade_match.group(2)) if grade_match.group(2) else start_grade
        if end_grade <= 5:
            matches.add("School Age")
        else:
            matches.add("Teens")

    return ", ".join(sorted(matches))

def is_cancelled(name, description):
    return "cancelled" in name.lower() or "canceled" in description.lower()

def scrape_nnpl_events(mode="all"):
    print("\U0001F4DA Scraping Newport News Public Library events from iCal feed...")

    today = datetime.now(timezone.utc)

    if mode == "weekly":
        date_range_start = today
        date_range_end = today + timedelta(days=7)
    
    elif mode == "monthly":
        date_range_start = datetime(today.year, today.month, 1, tzinfo=timezone.utc)
        if today.month == 12:
            next_month = datetime(today.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            next_month = datetime(today.year, today.month + 1, 1, tzinfo=timezone.utc)
        date_range_end = next_month - timedelta(seconds=1)
    
    else:
        date_range_start = today
        date_range_end = today + timedelta(days=90)

    resp = requests.get(ICAL_URL)
    calendar = Calendar(resp.text)
    program_type_to_categories = LIBRARY_CONSTANTS["nnpl"].get("program_type_to_categories", {})

    events = []
    for event in calendar.events:
        try:
            print(f"🧪 Evaluating: {event.name}")

            if event.begin is None:
                print("⏭️ Skipping: No start time")
                continue
            
            event_date = event.begin.datetime.astimezone(timezone.utc)
            
            # Extract event ID and timestamp from UID like: TKF/.../<eventId>/<timestamp>/...
            if uid_match:
                event_id, timestamp = uid_match.groups()
                event_link = f"https://tockify.com/nnlibrary/detail/{event_id}/{timestamp}?tags=Event"
            else:
                print(f"⚠️ UID format unrecognized → {event.uid}")
                event_link = "https://library.nnva.gov/264/Events-Calendar"

            if event_id_match:
                event_id, timestamp = event_id_match[0]
                event_link = f"https://tockify.com/nnlibrary/detail/{event_id}/{timestamp}?tags=Event"
            else:
                print(f"⚠️ Unexpected UID format: {event.uid}")
                event_link = "https://library.nnva.gov/264/Events-Calendar"

            # === Extract tags from event page (e.g. "Adults", "PhotoEditing") ===

            program_type = ""  # or populate this using keyword inference if you want it visible on the sheet
  
            if event_date < date_range_start or event_date > date_range_end:
                print(f"⏭️ Skipping: Outside date range ({event_date.date()})")
                continue

            name = event.name.strip() if event.name else ""
            description = event.description.strip() if event.description else ""
    
            if is_likely_adult_event(name) or is_likely_adult_event(description):
                print(f"⏭️ Skipping: Adult event → {name}")
                continue
    
            raw_location_html = event.location or ""
            raw_location = BeautifulSoup(raw_location_html, "html.parser").get_text().strip()
            location_name = raw_location.split(",")[0].strip()
            if not location_name:
                print(f"⏭️ Skipping: Missing location → {name} / raw location: {repr(raw_location)}")
                continue

            if is_likely_adult_event(name) or is_likely_adult_event(description):
                continue

            combined_text = f"{name} {description}".lower()
            categories = ""
            for keyword, cat in program_type_to_categories.items():
                if keyword.lower() in combined_text:
                    categories = cat
                    break

            if not location_name:
                continue
            location = LIBRARY_CONSTANTS["nnpl"]["venue_names"].get(location_name)
            if not location:
                print(f"\U0001F4CC Unmapped location: {repr(raw_location)}")
                location = location_name
            
            start_dt = event.begin.datetime.astimezone(eastern)
            if event.end and event.end.datetime:
                raw_end_dt = event.end.datetime
                if raw_end_dt == event.begin.datetime:
                    end_dt = start_dt + timedelta(hours=1)
                else:
                    end_dt = raw_end_dt.astimezone(eastern)
            else:
                end_dt = start_dt + timedelta(hours=1)

            start_time = start_dt.strftime("%-I:%M %p")
            end_time = end_dt.strftime("%-I:%M %p")
            time_str = f"{start_time} - {end_time}"

            events.append({
                "Event Name": name,
                "Event Link": event_link,
                "Event Status": "Cancelled" if is_cancelled(name, description) else "Available",
                "Time": time_str,
                "Ages": extract_ages(name + " " + description),
                "Location": location,
                "Month": event_date.strftime("%b"),
                "Day": str(event_date.day),
                "Year": str(event_date.year),
                "Event Date": event_date.strftime("%Y-%m-%d"),
                "Event End Date": end_dt.strftime("%Y-%m-%d"),
                "Event Description": description,
                "Series": "",
                "Program Type": program_type,
                "Categories": categories
            })
        except Exception as e:
            print(f"\u26A0\uFE0F Error parsing event: {e}")

    print(f"\u2705 Scraped {len(events)} events from Newport News Public Library.")
    return events
