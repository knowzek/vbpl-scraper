import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re

CID = 4688  # Suffolk Public Library Calendar ID
BASE_URL = "https://suffolkpubliclibrary.libcal.com/ajax/calendar/list"


def is_likely_adult_event(text):
    text = text.lower()
    keywords = [
        "adult", "18+", "21+", "job help", "resume", "medicare",
        "investment", "retirement", "social security", "veterans",
        "seniors", "tax help", "real estate", "finance", "knitting"
    ]
    return any(kw in text for kw in keywords)


def extract_ages(text):
    text = text.lower()
    matches = set()

    if any(kw in text for kw in ["infants", "babies", "baby", "birth to 2", "0-2"]):
        matches.add("Infant")
    if any(kw in text for kw in ["toddlers", "2-3", "2 and 3", "age 2", "age 3"]):
        matches.add("Preschool")
    if any(kw in text for kw in ["preschool", "ages 3-5", "3-5"]):
        matches.add("Preschool")
    if any(kw in text for kw in ["school age", "elementary", "5-8", "ages 5", "grade"]):
        matches.add("School Age")
    if any(kw in text for kw in ["tween", "tweens", "middle school"]):
        matches.add("Tweens")
    if any(kw in text for kw in ["teen", "teens", "high school"]):
        matches.add("Teens")
    if "all ages" in text:
        matches.add("All Ages")
    return ", ".join(sorted(matches))


def scrape_spl_events(mode="all"):
    print("🧭 Scraping Suffolk Public Library events...")

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
        end_date = today + timedelta(days=90)

    events = []
    page = 0

    while True:
        print(f"🔄 Fetching page offset {page}...")
        params = {
            "cid": CID,
            "page": page,
            "perpage": 48,
            "c": -1,
            "inc": 0,
            "t": "g",
            "d": "0000-00-00"
        }

        resp = requests.get(BASE_URL, params=params)
        if not resp.headers.get("Content-Type", "").startswith("application/json"):
            print("❌ Non-JSON response:")
            print(resp.text[:300])
            break

        data = resp.json()
        results = data.get("results", [])

        if not results:
            break

        for result in results:
            try:
                dt = datetime.strptime(result["startdt"], "%Y-%m-%d %H:%M:%S")
                end_dt = datetime.strptime(result["enddt"], "%Y-%m-%d %H:%M:%S")

                if dt > end_date:
                    continue

                name = result.get("title", "").strip()
                desc = result.get("description", "").strip()
                if is_likely_adult_event(name) or is_likely_adult_event(desc):
                    continue

                start = result.get("start", "")
                end = result.get("end", "")
                if result.get("all_day", False):
                    time_str = "All Day Event"
                elif start and end:
                    time_str = f"{start} – {end}"
                elif start:
                    time_str = start
                else:
                    time_str = ""

                location = result.get("location", "Suffolk Public Library").strip()
                url = result.get("url", "").strip()

                ages = extract_ages(name + " " + desc)

                events.append({
                    "Event Name": name,
                    "Event Link": url,
                    "Event Status": "Available",
                    "Time": time_str,
                    "Ages": ages,
                    "Location": location,
                    "Month": dt.strftime("%b"),
                    "Day": str(dt.day),
                    "Year": str(dt.year),
                    "Event Date": dt.strftime("%Y-%m-%d"),
                    "Event End Date": end_dt.strftime("%Y-%m-%d"),
                    "Event Description": desc,
                    "Series": "",
                    "Program Type": "",
                    "Categories": ""
                })

            except Exception as e:
                print(f"⚠️ Error parsing event: {e}")

        if len(results) < 48:
            break
        page += 48

    print(f"✅ Scraped {len(events)} events from SPL.")
    return events
