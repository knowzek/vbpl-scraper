import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import re


BASE_URL = "https://norfolk.libcal.com"
CALENDAR_URL = f"{BASE_URL}/calendars?cid=-1&t=g&d=0000-00-00&cal=-1&inc=0"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def filter_events_by_mode(events, mode):
    today = datetime.today()

    if mode == "weekly":
        end_date = today + timedelta(days=7)
    elif mode == "monthly":
        if today.month == 12:
            next_month = datetime(today.year + 1, 1, 1)
        else:
            next_month = datetime(today.year, today.month + 1, 1)

        if next_month.month == 12:
            following_month = datetime(next_month.year + 1, 1, 1)
        else:
            following_month = datetime(next_month.year, next_month.month + 1, 1)

        end_date = following_month - timedelta(days=1)
    else:
        return events

    filtered = []
    for event in events:
        try:
            edate = datetime.strptime(event["Event Date"], "%Y-%m-%d")
            if today <= edate <= end_date:
                filtered.append(event)
        except:
            continue
    return filtered


def scrape_npl_events(mode="monthly"):
    print("🌐 Scraping Norfolk Public Library events...")
    session = requests.Session()
    session.headers.update(HEADERS)

    response = session.get(CALENDAR_URL, timeout=30)
    soup = BeautifulSoup(response.text, "html.parser")
    events = []

    for card in soup.select(".fc-event"):  # LibCal uses FullCalendar structure
        try:
            title_tag = card.select_one(".fc-title")
            name = title_tag.get_text(strip=True) if title_tag else "Untitled Event"

            link_tag = card.get("href") or card.get("data-href")
            link = BASE_URL + link_tag if link_tag and link_tag.startswith("/") else link_tag
            if not link:
                continue

            # Parse date
            data_start = card.get("data-start")
            if not data_start:
                continue
            event_date = datetime.strptime(data_start[:10], "%Y-%m-%d")
            month_text = event_date.strftime("%b")
            day_text = event_date.strftime("%d")
            year_text = event_date.strftime("%Y")

            # Fetch detail page
            time.sleep(0.5)
            detail_response = session.get(link, timeout=20)
            detail_soup = BeautifulSoup(detail_response.text, "html.parser")

            description = detail_soup.select_one(".s-lc-event-desc")
            description_text = description.get_text(strip=True) if description else ""

            location = detail_soup.select_one(".s-lc-event-location")
            location_text = location.get_text(strip=True) if location else ""

            time_tag = detail_soup.select_one(".s-lc-event-time")
            time_text = time_tag.get_text(strip=True) if time_tag else ""

            ages = ""
            program_type = ""
            status = "Available"
            series = ""

            events.append({
                "Event Name": name,
                "Event Link": link,
                "Event Status": status,
                "Time": time_text,
                "Ages": ages,
                "Location": location_text,
                "Month": month_text,
                "Day": day_text,
                "Year": year_text,
                "Event Date": event_date.strftime("%Y-%m-%d"),
                "Event Description": description_text,
                "Series": series,
                "Program Type": program_type,
            })

        except Exception as e:
            print(f"⚠️ Error processing event card: {e}")

    print(f"✅ Scraped {len(events)} total events from Norfolk.")

    return filter_events_by_mode(events, mode)
