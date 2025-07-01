# scrape_nnpl_events.py

import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

BASE_CALENDAR = "https://tockify.com/nnlibrary"
FEED_URL = "https://public.tockify.com/feeds/nnlibrary/list.json"

def scrape_nnpl_events(mode="all"):
    print("📅 Scraping NNPL (Tockify) event calendar...")

    today = datetime.today()
    if mode == "weekly":
        date_cutoff = today + timedelta(days=7)
    elif mode == "monthly":
        if today.month == 12:
            next_month = datetime(today.year + 1, 1, 1)
        else:
            next_month = datetime(today.year, today.month + 1, 1)
        if next_month.month == 12:
            following = datetime(next_month.year + 1, 1, 1)
        else:
            following = datetime(next_month.year, next_month.month + 1, 1)
        date_cutoff = following - timedelta(days=1)
    else:
        date_cutoff = today + timedelta(days=90)

    try:
        resp = requests.get(FEED_URL, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"❌ Failed to fetch Tockify feed: {e}")
        return []

    events = []

    for item in data.get("items", []):
        try:
            dt = datetime.fromtimestamp(item["start"] / 1000)

            if dt > date_cutoff:
                continue

            event_id = item["id"]
            event_link = f"{BASE_CALENDAR}/detail/{event_id}/{item['start']}"

            # Fetch event detail page
            try:
                detail_resp = requests.get(event_link, timeout=15)
                detail_soup = BeautifulSoup(detail_resp.text, "html.parser")
            except Exception as err:
                print(f"⚠️ Failed to fetch event detail for ID {event_id}: {err}")
                continue

            # Extract content
            title_tag = detail_soup.select_one(".title-text")
            title = title_tag.get_text(strip=True) if title_tag else item.get("title", "Untitled Event")

            desc_tag = detail_soup.select_one(".description")
            description = desc_tag.get_text("\n\n", strip=True) if desc_tag else ""

            location_tag = detail_soup.select_one(".location")
            location = location_tag.get_text(strip=True) if location_tag else ""

            time_tag = detail_soup.select_one(".time")
            time_text = time_tag.get_text(strip=True) if time_tag else ""

            # Normalize time display
            time_str = time_text if time_text else "All Day Event"

            events.append({
                "Event Name": title,
                "Event Link": event_link,
                "Event Status": "Available",
                "Time": time_str,
                "Ages": "",
                "Location": location,
                "Month": dt.strftime("%b"),
                "Day": str(dt.day),
                "Year": str(dt.year),
                "Event Date": dt.strftime("%Y-%m-%d"),
                "Event End Date": dt.strftime("%Y-%m-%d"),
                "Event Description": description,
                "Series": "",
                "Program Type": ""
            })

        except Exception as e:
            print(f"⚠️ Error processing item: {e}")

    print(f"✅ Scraped {len(events)} events from NNPL.")
    return events
