from datetime import datetime, timedelta, timezone
import requests
from ics import Calendar
from bs4 import BeautifulSoup
from constants import LIBRARY_CONSTANTS
import re

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
        "blackout poetry"
    ]
    return any(kw in text for kw in keywords)

def extract_tags(text):
    matches = re.findall(r"\b(?:Event|[A-Z][a-z]+(?:[A-Z][a-z]+)*)\b", text)
    return ", ".join(set(matches)) if matches else ""

def extract_ages(text):
    text = text.lower()
    matches = []

    if any(kw in text for kw in ["infants", "babies", "baby", "0-2"]):
        matches.append("Infant")
    if any(kw in text for kw in ["preschool", "toddlers", "age 2", "aged 2", "ages 2", "2-year-olds"]):
        matches.append("Preschool")
    if any(kw in text for kw in ["school age", "grades", "k-", "elementary", "children ages 5", "school-age"]):
        matches.append("School Age")
    if "teen" in text or "teens" in text or "middle school" in text or "high school" in text:
        matches.append("Teens")
    if any(kw in text for kw in ["18+", "adults", "adult", "grown-ups"]):
        matches.append("Adults 18+")

    return ", ".join(matches)

def is_cancelled(name, description):
    return "cancelled" in name.lower() or "canceled" in description.lower()

def scrape_nnpl_events(mode="all"):
    print("\U0001F4DA Scraping Newport News Public Library events from iCal feed...")

    today = datetime.now(timezone.utc)
    if mode == "weekly":
        date_range_end = today + timedelta(days=7)
    elif mode == "monthly":
        if today.month == 12:
            next_month = datetime(today.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            next_month = datetime(today.year, today.month + 1, 1, tzinfo=timezone.utc)
        if next_month.month == 12:
            following_month = datetime(next_month.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            following_month = datetime(next_month.year, next_month.month + 1, 1, tzinfo=timezone.utc)
        date_range_end = following_month - timedelta(days=1)
    else:
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
            if event_date > date_range_end:
                print("⏭️ Skipping: Future date")
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
                print(f"⏭️ Skipping: Missing location → {name}")
                continue
    
            event_link = None
            if description:
                preferred = re.search(r"https://tockify.com/[^\s<>\"']+", description)
                if preferred:
                    event_link = preferred.group(0)
                else:
                    fallback = re.search(r"https?://[^\s<>\"']+", description)
                    if fallback:
                        event_link = fallback.group(0)
            if not event_link:
                print(f"⏭️ Skipping: No event link → {name}")
                continue


            name = event.name.strip() if event.name else ""
            description = event.description.strip() if event.description else ""

            if is_likely_adult_event(name) or is_likely_adult_event(description):
                continue

            program_type = extract_tags(description)
            categories = ""
            for keyword, cat in program_type_to_categories.items():
                if keyword.lower() in program_type.lower():
                    categories = cat
                    break

            raw_location_html = event.location or ""
            raw_location = BeautifulSoup(raw_location_html, "html.parser").get_text().strip()
            location_name = raw_location.split(",")[0].strip()
            if not location_name:
                continue
            location = LIBRARY_CONSTANTS["nnpl"]["venue_names"].get(location_name)
            if not location:
                print(f"\U0001F4CC Unmapped location: {repr(raw_location)}")
                location = location_name

            event_link = None
            if description:
                preferred = re.search(r"https://tockify.com/[^\s<>\"']+", description)
                if preferred:
                    event_link = preferred.group(0)
                else:
                    fallback = re.search(r"https?://[^\s<>\"']+", description)
                    if fallback:
                        event_link = fallback.group(0)
            if not event_link:
                continue

            start_time = event.begin.datetime.astimezone(timezone.utc).strftime("%-I:%M %p")
            end_time = event.end.datetime.astimezone(timezone.utc).strftime("%-I:%M %p") if event.end else ""
            time_str = f"{start_time} - {end_time}" if end_time else start_time

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
                "Event End Date": event.end.datetime.astimezone(timezone.utc).strftime("%Y-%m-%d") if event.end else event_date.strftime("%Y-%m-%d"),
                "Event Description": description,
                "Series": "",
                "Program Type": program_type,
                "Categories": categories
            })
        except Exception as e:
            print(f"\u26A0\uFE0F Error parsing event: {e}")

    print(f"\u2705 Scraped {len(events)} events from Newport News Public Library.")
    return events
