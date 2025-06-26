import requests
from datetime import datetime
import time

def scrape_npl_events(mode="all"):
    print("🌐 Scraping Norfolk Public Library events via JSON feed...")

    url = "https://norfolk.libcal.com/ajax/calendar/list"
    headers = {
        "User-Agent": "Mozilla/5.0",
    }

    events = []

    params = {
        "cid": -1,
        "cal": -1,
        "inc": 0,
        "t": "g",
        "d": "0000-00-00"
    }

    resp = requests.get(url, params=params, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results", [])

    for result in results:
        try:
            start_raw = result.get("startdt")
            if not start_raw:
                continue

            dt = datetime.strptime(start_raw, "%Y-%m-%d %H:%M:%S")
            month = dt.strftime("%b")
            day = str(dt.day)
            year = str(dt.year)

            events.append({
                "Event Name": result.get("title", "").strip(),
                "Event Link": result.get("url", ""),  # if present
                "Event Status": "Available",
                "Time": result.get("fromTime", ""),
                "Ages": "",
                "Location": result.get("location", "").strip(),
                "Month": month,
                "Day": day,
                "Year": year,
                "Event Date": dt.strftime("%Y-%m-%d"),
                "Event Description": result.get("description", "").strip(),
                "Series": "",
                "Program Type": "",
            })
        except Exception as e:
            print(f"⚠️ Error parsing event: {e}")

    print(f"✅ Scraped {len(events)} total events from Norfolk.")
    return events
