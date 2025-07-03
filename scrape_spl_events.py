import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re

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

    today = datetime.now()
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
        print(f"🔄 Fetching page {page}...")
        url = f"https://suffolkpubliclibrary.libcal.com/ajax/calendar/list?c=-1&date=0000-00-00&perpage=48&page={page}"
        resp = requests.get(url)
        if not resp.ok:
            print("❌ Failed to load page.")
            break
        data = resp.json()
        if not data:
            break

        for item in data:
            try:
                dt = datetime.strptime(item["start"], "%Y-%m-%d %H:%M:%S")
                if mode == "weekly" and dt > today + timedelta(days=7):
                    continue
                elif mode == "monthly" and dt > end_date:
                    continue

                title = item.get("title", "").strip()
                desc = item.get("description", "").strip()
                if is_likely_adult_event(title) or is_likely_adult_event(desc):
                    continue

                start = item.get("start", "")
                end = item.get("end", "")
                time_str = "All Day Event" if item.get("all_day", False) else (f"{start} – {end}" if end else start)

                ages = extract_ages(title + " " + desc)

                events.append({
                    "Event Name": title,
                    "Event Link": item.get("url", ""),
                    "Event Status": "Available",
                    "Time": time_str,
                    "Ages": ages,
                    "Location": item.get("location", "Suffolk Public Library"),
                    "Month": dt.strftime("%b"),
                    "Day": str(dt.day),
                    "Year": str(dt.year),
                    "Event Date": dt.strftime("%Y-%m-%d"),
                    "Event End Date": dt.strftime("%Y-%m-%d"),
                    "Event Description": desc,
                    "Series": "",
                    "Program Type": "",
                    "Categories": ""
                })

            except Exception as e:
                print(f"⚠️ Error processing event: {e}")

        if len(data) < 48:
            break
        page += 1

    print(f"✅ Scraped {len(events)} events from SPL.")
    return events
