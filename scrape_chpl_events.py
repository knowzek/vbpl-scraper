import requests
from datetime import datetime, timedelta
import json


def scrape_chpl_events(mode="all"):
    print("✨ Scraping Chesapeake Public Library events...")

    today = datetime.today()
    base_url = "https://events.chesapeakelibrary.org/eeventcaldata"

    if mode == "weekly":
        days = 7
    elif mode == "monthly":
        days = 31
    else:
        days = 90  # Default fetch 90 days if no filter

    payload = {
        "private": False,
        "date": today.strftime("%Y-%m-%d"),
        "days": days,
        "locations": [],
        "ages": [],
        "types": []
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest"
    }

    response = requests.get(
        base_url,
        params={"event_type": 0, "req": json.dumps(payload)},
        headers=headers,
        timeout=20
    )
    response.raise_for_status()
    data = response.json()

    events = []

    for item in data:
        print(json.dumps(item, indent=2))
        try:
            dt = datetime.strptime(item["event_start"], "%Y-%m-%d %H:%M:%S")

            if mode == "weekly" and dt > today + timedelta(days=7):
                continue
            elif mode == "monthly" and dt > today + timedelta(days=32):
                continue

            # Time logic
            time_str = item.get("time_string", "")
            if time_str.lower() in ("all day", "all day event"):
                time_str = "All Day Event"

            ages = item.get("ages", "")

            events.append({
                "Event Name": item.get("title", "").strip(),
                "Event Link": item.get("url", "").replace("\\/", "/"),
                "Event Status": "Available",
                "Time": time_str,
                "Ages": ages,
                "Location": item.get("location", "").strip(),
                "Month": dt.strftime("%b"),
                "Day": str(dt.day),
                "Year": str(dt.year),
                "Event Date": dt.strftime("%Y-%m-%d"),
                "Event Description": item.get("description", "").strip(),
                "Series": "Yes" if item.get("recurring_id") else "",
                "Program Type": item.get("tags", "")
            })

        except Exception as e:
            print(f"⚠️ Error processing event: {e}")

    print(f"✅ Scraped {len(events)} events from Chesapeake.")
    return events
