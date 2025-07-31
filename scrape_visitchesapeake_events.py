import requests
from datetime import datetime, timedelta
from constants import TITLE_KEYWORD_TO_CATEGORY, UNWANTED_TITLE_KEYWORDS
import re
import json


def extract_ages(text):
    text = text.lower()
    matches = set()
    if any(kw in text for kw in ["baby", "babies", "infant", "0-2"]):
        matches.add("Infant")
    if any(kw in text for kw in ["preschool", "toddler", "ages 3-5", "age 2", "age 3"]):
        matches.add("Preschool")
    if any(kw in text for kw in ["school age", "grade", "elementary", "5-12", "ages 6-11"]):
        matches.add("School Age")
    if any(kw in text for kw in ["teen", "high school", "middle school", "13-17"]):
        matches.add("Teens")
    if "all ages" in text:
        matches.add("All Ages")
    return ", ".join(sorted(matches))


def scrape_visitchesapeake_events(mode="all"):
    print("🌾 Scraping Visit Chesapeake events via JSON endpoint...")

    today = datetime.now()
    if mode == "weekly":
        cutoff = today + timedelta(days=7)
    elif mode == "monthly":
        cutoff = today + timedelta(days=31)
    else:
        cutoff = today + timedelta(days=90)

    start_date = today.isoformat()
    end_date = cutoff.isoformat()
    url = "https://www.visitchesapeake.com/includes/rest_v2/plugins_events_events_by_date/find/"

    events = []
    seen = set()
    skip = 0
    limit = 100

    while True:
        payload = {
            "filter": {
                "categories.catId": {"$in": ["1016"]},
                "date_range": {
                    "start": {"$date": start_date},
                    "end": {"$date": end_date}
                }
            },
            "options": {
                "skip": skip,
                "limit": limit,
                "sort": {"date": 1},
                "fields": {
                    "title": 1,
                    "typeName": 1,
                    "categories": 1,
                    "startDate": 1,
                    "endDate": 1,
                    "description": 1,
                    "location": 1,
                    "address1": 1,
                    "linkUrl": 1,
                    "url": 1
                },
                "count": True
            }
        }

        try:
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest"
            }

            res = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )

            res.raise_for_status()
            data = res.json()
            docs = data.get("docs", [])
        except Exception as e:
            print(f"❌ Error fetching page {skip//limit + 1}: {e}")
            break

        if not docs:
            break

        for item in docs:
            try:
                if item.get("typeName") != "One-Time Event":
                    continue
                if "title" not in item:
                    continue

                name = item["title"].strip()
                if name in seen:
                    continue
                seen.add(name)

                desc = item.get("description", "").strip()
                text_to_match = f"{name} {desc}".lower()
                if any(kw in text_to_match for kw in UNWANTED_TITLE_KEYWORDS):
                    continue

                start_raw = item.get("startDate", "")
                try:
                    start_dt = datetime.strptime(start_raw[:10], "%Y-%m-%d")
                except:
                    continue

                if start_dt < today or start_dt > cutoff:
                    continue

                link = item.get("linkUrl") or ("https://www.visitchesapeake.com" + item.get("url", ""))
                location = item.get("location") or item.get("address1", "")
                ages = extract_ages(name + " " + desc)

                keyword_tags = []
                for keyword, tag_string in TITLE_KEYWORD_TO_CATEGORY.items():
                    if keyword.lower() in text_to_match:
                        keyword_tags.extend(tag_string.split(","))
                keyword_category_str = ", ".join(sorted(set(keyword_tags)))

                categories = ", ".join(filter(None, [
                    "Event Location - Chesapeake",
                    "Audience - Free Event",
                    keyword_category_str
                ]))

                events.append({
                    "Event Name": f"{name} (Chesapeake)",
                    "Event Link": link,
                    "Event Status": "Available",
                    "Time": "",
                    "Ages": ages,
                    "Location": location,
                    "Month": start_dt.strftime("%b"),
                    "Day": str(start_dt.day),
                    "Year": str(start_dt.year),
                    "Event Description": desc,
                    "Series": "",
                    "Program Type": "Family Fun",
                    "Categories": categories
                })
            except Exception as e:
                print(f"⚠️ Error processing item: {e}")

        skip += len(docs)
        if len(docs) < limit:
            break

    print(f"✅ Scraped {len(events)} Visit Chesapeake events.")
    return events
