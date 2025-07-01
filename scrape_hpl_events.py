import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re


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
        "crafts for adults", "finance", "retirement"
    ]
    return any(kw in text for kw in keywords)

# moved to constants.py; imported instead

from constants import LIBRARY_CONSTANTS

def scrape_hpl_events(mode="all"):
    print("📚 Scraping Hampton Public Library events...")

    BASE_URL = "https://www.hampton.gov"
    CALENDAR_URL = f"{BASE_URL}/calendar.aspx?CID=24&showPastEvents=false"

    today = datetime.today()

    if mode == "weekly":
        date_range_end = today + timedelta(days=7)
    elif mode == "monthly":
        if today.month == 12:
            next_month = datetime(today.year + 1, 1, 1)
        else:
            next_month = datetime(today.year, today.month + 1, 1)
        if next_month.month == 12:
            following_month = datetime(next_month.year + 1, 1, 1)
        else:
            following_month = datetime(next_month.year, next_month.month + 1, 1)
        date_range_end = following_month - timedelta(days=1)
    else:
        date_range_end = today + timedelta(days=90)  # Arbitrary large range

    response = requests.get(CALENDAR_URL, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    print(soup.prettify()[:8000])  # just a snippet

    event_blocks = soup.select(".catAgendaItem")
    events = []

    for block in event_blocks:
        try:
            title_link = block.select_one("a")
            if not title_link:
                continue

            event_name = title_link.get_text(strip=True)
            event_link = BASE_URL + title_link["href"]

            date_block = block.select_one(".catAgendaDate")
            if not date_block:
                continue
            date_str = date_block.get_text(strip=True)
            try:
                event_date = datetime.strptime(date_str, "%A, %B %d, %Y")
            except ValueError:
                continue

            if event_date > date_range_end:
                continue

            # Visit detail page for time, description, location
            detail_resp = requests.get(event_link, timeout=15)
            detail_soup = BeautifulSoup(detail_resp.text, "html.parser")

            description_tag = detail_soup.select_one("#main-content")
            if description_tag:
                for br in description_tag.find_all("br"):
                    br.replace_with("\n")
                description = description_tag.get_text(separator="\n\n", strip=True)
            else:
                description = ""

            # Skip adult events
            if is_likely_adult_event(event_name) or is_likely_adult_event(description):
                continue

            time_match = re.search(r"\b(\d{1,2}:\d{2}\s*[APMapm]{2})\b", description)
            time_str = time_match.group(1) if time_match else ""

            program_type = ""
            categories = ""
            combined_text = f"{event_name} {description}".lower()
            program_type_to_categories = LIBRARY_CONSTANTS["hpl"].get("program_type_to_categories", {})
            for keyword, cat in program_type_to_categories.items():
                if keyword in combined_text:
                    program_type = keyword.capitalize()
                    categories = cat
                    break

            events.append({
                "Event Name": event_name,
                "Event Link": event_link,
                "Event Status": "Available",
                "Time": time_str,
                "Ages": "",
                "Location": "Hampton Public Library",
                "Month": event_date.strftime("%b"),
                "Day": str(event_date.day),
                "Year": str(event_date.year),
                "Event Date": event_date.strftime("%Y-%m-%d"),
                "Event End Date": event_date.strftime("%Y-%m-%d"),
                "Event Description": description,
                "Series": "",
                "Program Type": program_type,
                "Categories": categories
            })
        except Exception as e:
            print(f"⚠️ Error parsing event block: {e}")

    print(f"✅ Scraped {len(events)} events from Hampton Public Library.")
    return events
