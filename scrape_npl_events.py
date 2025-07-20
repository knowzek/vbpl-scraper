import requests
from datetime import datetime, timedelta
from time import sleep
from bs4 import BeautifulSoup
import re
from constants import UNWANTED_TITLE_KEYWORDS

def scrape_npl_events(mode="all"):
    print("🌐 Scraping Norfolk Public Library events via JSON feed...")

    events = []
    page = 1
    while True:
        print(f"🔄 Fetching page {page}...")
        # Set the date param based on mode
        if mode == "monthly":
            date_param = datetime.today().strftime("%Y-%m-01")  # First of the month
        elif mode == "weekly":
            date_param = datetime.today().strftime("%Y-%m-%d")  # Today
        else:
            date_param = "0000-00-00"  # All (default fallback)
        
        url = f"https://norfolk.libcal.com/ajax/calendar/list?c=-1&date={date_param}&perpage=48&page={page}&audience=&cats=&camps=&inc=0"

        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])

        if not results:
            break

        for result in results:
            try:
                title = result.get("title", "").strip()
                # 🚫 Skip unwanted titles
                if any(bad_word in title.lower() for bad_word in UNWANTED_TITLE_KEYWORDS):
                    print(f"⏭️ Skipping: Unwanted title match → {title}")
                    continue
                dt = datetime.strptime(result["startdt"], "%Y-%m-%d %H:%M:%S")
                end_dt = datetime.strptime(result["enddt"], "%Y-%m-%d %H:%M:%S")

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
                if len(audiences) == 1 and audiences[0].get("name", "").strip() == "Adults (18+)":
                    continue

                ages = ", ".join([a.get("name", "") for a in audiences if "name" in a])

                # Fallback: infer Adults 18+ from breadcrumb if no ages
                if not ages.strip():
                    try:
                        detail_url = result.get("url", "")
                        detail_resp = requests.get(detail_url, timeout=10)
                        detail_soup = BeautifulSoup(detail_resp.text, "html.parser")
                        breadcrumb_links = detail_soup.select("nav[aria-label='breadcrumb'] a")
                        print(f"🔎 Breadcrumb for {result.get('title')}: {[link.get_text() for link in breadcrumb_links]}")
                        for link in breadcrumb_links:
                            if "Adult Programs" in link.get_text():
                                ages = "Adults 18+"
                                break

                    # Secondary: check tag links if still blank
                        if not ages.strip():
                            tag_links = detail_soup.select("a[href*='/calendar?cid=']")
                            for tag in tag_links:
                                if "Adult Programs" in tag.get_text():
                                    ages = "Adults 18+"
                                    break
                    except Exception as e:
                        print(f"⚠️ Failed to fetch breadcrumb for {result.get('title')}: {e}")

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

                # Get initial location
                location = result.get("campus", "").strip() or result.get("location", "").strip()

                # Fallback: infer from "@ Tucker"
                if not location:
                    match = re.search(r"@ ([\w\- ]+)", result.get("title", ""))
                    if match:
                        short_name = match.group(1).strip()
                        name_map = {
                            "Tucker": "Richard A. Tucker Memorial Library",
                            "Pretlow": "Mary D. Pretlow Anchor Branch Library",
                            "Barron F. Black": "Barron F. Black Branch Library",
                            "Jordan-Newby": "Jordan-Newby Anchor Branch Library at Broad Creek",
                            "Blyden": "Blyden Branch Library",
                            "Lafayette": "Lafayette Branch Library",
                            "Larchmont": "Larchmont Branch Library",
                            "Van Wyck": "Van Wyck Branch Library",
                            "Downtown": "Downtown Branch at Slover",
                            "Park Place": "Park Place Branch Library",
                            "Little Creek": "Little Creek Branch Library",
                            "Janaf": "Janaf Branch Library"
                        }
                        for key, full_name in name_map.items():
                            if short_name.lower() in key.lower():
                                location = full_name
                                break

                # Append event
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
                    "Event End Date": end_dt.strftime("%Y-%m-%d"),
                    "Event Description": result.get("description", "").strip(),
                    "Series": "",
                    "Program Type": "",
                })

            except Exception as e:
                print(f"⚠️ Error parsing event: {e}")

        if len(results) < 48:
            break

        page += 1
        sleep(0.5)

    print(f"✅ Scraped {len(events)} events total.")
    return events
