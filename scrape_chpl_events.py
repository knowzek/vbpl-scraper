import requests
from datetime import datetime, timedelta
import json
from bs4 import BeautifulSoup
from constants import UNWANTED_TITLE_KEYWORDS, TITLE_KEYWORD_TO_CATEGORY, LIBRARY_CONSTANTS


def scrape_chpl_events(mode="all"):
    print("✨ Scraping Chesapeake Public Library events...")

    today = datetime.today()
    base_url = "https://events.chesapeakelibrary.org/eeventcaldata"

    if mode == "weekly":
        days = 7
    elif mode == "monthly":
        days = 30
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
        try:
            dt = datetime.strptime(item["event_start"], "%Y-%m-%d %H:%M:%S")

            if mode == "weekly" and dt > today + timedelta(days=7):
                continue

            # Time logic
            time_str = item.get("time_string", "")
            if time_str.lower() in ("all day", "all day event"):
                time_str = "All Day Event"

            ages = item.get("ages", "")

            title = item.get("title", "").strip()

            # 🚫 Skip unwanted titles
            if any(bad_word in title.lower() for bad_word in UNWANTED_TITLE_KEYWORDS):
                print(f"⏭️ Skipping: Unwanted title match → {title}")
                continue
            
            event_url = item.get("url", "").replace("\\/", "/")
            status = "Available"
            
            # ✅ Check for cancellation
            if item.get("changed") == "1":
                try:
                    detail_resp = requests.get(event_url, timeout=10)
                    detail_soup = BeautifulSoup(detail_resp.text, "html.parser")
                    cancelled_msg = detail_soup.select_one(".eelist-changed-message")
                    if cancelled_msg and "cancelled" in cancelled_msg.get_text(strip=True).lower():
                        status = "Cancelled"
                except Exception as e:
                    print(f"⚠️ Failed to fetch detail page for status check: {event_url} — {e}")
            
            # ✅ Category tagging from title + ages
            title_lower = title.lower()
            keyword_tags = [tag for keyword, tag in TITLE_KEYWORD_TO_CATEGORY.items() if keyword in title_lower]
            
            program_type_to_categories = LIBRARY_CONSTANTS["chpl"].get("program_type_to_categories", {})
            age_to_categories = LIBRARY_CONSTANTS["chpl"].get("age_to_categories", {})
            audience_keys = [a.strip() for a in ages.split(",") if a.strip()]
            age_tags = []
            for key in audience_keys:
                tags = age_to_categories.get(key)
                if tags:
                    age_tags.extend([t.strip() for t in tags.split(",")])
            
            all_categories = ", ".join(dict.fromkeys(keyword_tags + age_tags))  # dedupe while preserving order
            
            # ✅ Final event append
            events.append({
                "Event Name": title,
                "Event Link": event_url,
                "Event Status": status,
                "Time": time_str,
                "Ages": ages,
                "Location": item.get("location", "").strip(),
                "Month": dt.strftime("%b"),
                "Day": str(dt.day),
                "Year": str(dt.year),
                "Event Date": dt.strftime("%Y-%m-%d"),
                "Event Description": item.get("description", "").strip(),
                "Series": "Yes" if item.get("recurring_id") else "",
                "Program Type": item.get("tags", ""),
                "Categories": all_categories
            })
            
        except Exception as e:
            print(f"⚠️ Error processing event: {e}")
        
    print(f"✅ Scraped {len(events)} events from Chesapeake.")
    return events
