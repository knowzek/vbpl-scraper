import requests
from datetime import datetime, timedelta

def scrape_npl_events(mode="all"):
    print("🌐 Scraping Norfolk Public Library events via JSON feed...")

    url = "https://norfolk.libcal.com/ajax/calendar/list"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest"
    }

    params = {
        "c": -1,
        "date": "0000-00-00",
        "perpage": 100,
        "page": 1,
        "audience": "",
        "cats": "",
        "camps": "",
        "inc": 0
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    results = data.get("results", [])

    events = []
    for result in results:
        try:
            dt = datetime.strptime(result["startdt"], "%Y-%m-%d %H:%M:%S")

            if mode == "weekly":
                if dt > datetime.today() + timedelta(days=7):
                    continue
            elif mode == "monthly":
                today = datetime.today()
                if today.month == 12:
                    next_month = datetime(today.year + 1, 1, 1)
                else:
                    next_month = datetime(today.year, today.month + 1, 1)
                if next_month.month == 12:
                    following_month = datetime(next_month.year + 1, 1, 1)
                else:
                    following_month = datetime(next_month.year, next_month.month + 1, 1)
                last_day_next_month = following_month - timedelta(days=1)
                if dt > last_day_next_month:
                    continue

            events.append({
                "Event Name": result.get("title", "").strip(),
                "Event Link": result.get("url", ""),  # often present
                "Event Status": "Available",
                "Time": result.get("fromTime", ""),
                "Ages": "",
                "Location": result.get("location", "").strip(),
                "Month": dt.strftime("%b"),
                "Day": str(dt.day),
                "Year": str(dt.year),
                "Event Date": dt.strftime("%Y-%m-%d"),
                "Event Description": result.get("description", "").strip(),
                "Series": "",
                "Program Type": "",
            })
        except Exception as e:
            print(f"⚠️ Error parsing event: {e}")

    print(f"✅ Scraped {len(events)} total events from Norfolk.")
    return events
