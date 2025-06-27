import requests
from datetime import datetime
from time import sleep
from datetime import datetime, timedelta

def scrape_npl_events(mode="all"):
    print("🌐 Scraping Norfolk Public Library events via JSON feed...")

    events = []
    page = 1
    while True:
        print(f"🔄 Fetching page {page}...")
        url = f"https://norfolk.libcal.com/ajax/calendar/list?c=-1&date=0000-00-00&perpage=48&page={page}&audience=&cats=&camps=&inc=0"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])

        if not results:
            break

        for result in results:
            try:
                dt = datetime.strptime(result["startdt"], "%Y-%m-%d %H:%M:%S")

                if mode == "weekly" and dt > datetime.today() + timedelta(days=7):
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

                audiences = result.get("audiences", [])
                # 🚫 Skip events that are ONLY for Adults 18+
                if len(audiences) == 1 and audiences[0].get("name", "").strip() == "Adults (18+)":
                    continue

                ages = ", ".join([a.get("name", "") for a in audiences if "name" in a])
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

                events.append({
                    "Event Name": result.get("title", "").strip(),
                    "Event Link": result.get("url", ""),
                    "Event Status": "Available",
                    "Time": time_str,
                    "Ages": ages,
                    "Location": result.get("campus", "").strip() or result.get("location", "").strip(),
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

        if len(results) < 48:
            break

        page += 1
        sleep(0.5)  # Be polite to their server

    print(f"✅ Scraped {len(events)} events total.")
    return events
