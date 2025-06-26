import requests
from datetime import datetime
import time

def scrape_npl_events(mode="all"):
    print("🌐 Scraping Norfolk Public Library events via JSON feed...")

    url = "https://norfolk.libcal.com/ajax/events_list.php"
    headers = {
        "User-Agent": "Mozilla/5.0",
    }
    params = {
        "cid": -1,
        "c": -1,
        "audience[]": "",
        "page": 1,
        "perpage": 100,
        "date": "0000-00-00",  # special LibCal code to return all
    }

    all_events = []

    while True:
        print(f"🔄 Fetching page {params['page']}...")
        response = requests.get(url, params=params, headers=headers, timeout=20)
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        if not results:
            break

        for event in results:
            try:
                start_raw = event.get("startdt", "")
                if not start_raw:
                    continue

                dt = datetime.strptime(start_raw, "%Y-%m-%d %H:%M:%S")
                month = dt.strftime("%b")
                day = str(dt.day)
                year = str(dt.year)

                all_events.append({
                    "Event Name": event.get("title", "").strip(),
                    "Event Link": "",  # Not provided in JSON (optional enhancement later)
                    "Event Status": "Available",
                    "Time": event.get("fromTime", ""),
                    "Ages": "",  # Not provided in JSON
                    "Location": event.get("location", "").strip(),
                    "Month": month,
                    "Day": day,
                    "Year": year,
                    "Event Date": dt.strftime("%Y-%m-%d"),
                    "Event Description": event.get("description", "").strip(),
                    "Series": "",
                    "Program Type": "",  # Not present
                })
            except Exception as e:
                print(f"⚠️ Error parsing event: {e}")

        if len(results) < params["perpage"]:
            break  # no more pages
        params["page"] += 1
        time.sleep(0.25)

    print(f"✅ Scraped {len(all_events)} total events from Norfolk.")
    return all_events
