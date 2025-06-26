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
            # Clean up time string
            start = result.get("start", "").strip()
            end = result.get("end", "").strip()
            
            if result.get("all_day", False):
                time_str = "All Day Event"
            elif start and end:
                time_str = f"{start} – {end}"
            elif start:
                time_str = start
            else:
                time_str = ""
            
            # Clean up ages
            audiences = result.get("audiences", [])
            ages = ", ".join([a.get("name", "") for a in audiences if "name" in a])
            
            # Use 'campus' as the branch location
            location = result.get("campus", "").strip()
            
            # Final event dictionary
            events.append({
                "Event Name": result.get("title", "").strip(),
                "Event Link": result.get("url", ""),
                "Event Status": "Available",
                "Time": time_str,
                "Ages": ages,
                "Location": location,
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
