
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
from constants import TITLE_KEYWORD_TO_CATEGORY

def is_likely_adult_event(min_age):
    return min_age >= 18

def extract_ages(age_description):
    text = age_description.lower()
    matches = set()
    if any(kw in text for kw in ["infants", "babies", "baby", "0-2"]):
        matches.add("Infant")
    if any(kw in text for kw in ["preschool", "toddlers", "age 2", "age 3", "ages 3-5"]):
        matches.add("Preschool")
    if any(kw in text for kw in ["school age", "elementary", "ages 5", "grade", "5-12"]):
        matches.add("School Age")
    if any(kw in text for kw in ["teen", "teens", "middle school", "high school", "13-17"]):
        matches.add("Teens")
    if "all ages" in text:
        matches.add("All Ages")
    return ", ".join(sorted(matches))

def scrape_vbpr_events(mode="all"):
    print("🎯 Scraping Virginia Beach Parks & Rec events...")

    today = datetime.today()
    if mode == "weekly":
        cutoff = today + timedelta(days=7)
    elif mode == "monthly":
        cutoff = today + timedelta(days=31)
    else:
        cutoff = today + timedelta(days=90)

    events = []
    base_url = "https://anc.apm.activecommunities.com/vbparksrec/rest/activities/search"
    headers = {"Content-Type": "application/json"}
    total_pages = 36  # from inspection

    for page in range(1, total_pages + 1):
        print(f"🔄 Fetching page {page}...")
        payload = {
            "activity_select_param": 2,
            "viewMode": "list",
            "page_number": page,
            "locale": "en-US"
        }
        response = requests.post(base_url, json=payload, headers=headers)
        data = response.json()
        items = data.get("body", {}).get("activity_items", [])

        for item in items:
            try:
                name = item.get("name", "").strip()
                desc_html = item.get("desc", "")
                desc = BeautifulSoup(desc_html, "html.parser").get_text().strip()

                link = item.get("detail_url", "")
                status = item.get("urgent_message", {}).get("status_description", "Available")
                start_date = item.get("date_range_start", "")
                end_date = item.get("date_range_end", "")
                site = item.get("site", "").strip()
                time = item.get("time_range_landing_page", "") or item.get("time_range", "")
                category = item.get("category", "").strip()
                age_desc = item.get("age_description", "")
                min_age = item.get("age_min_year", 0)

                if not start_date:
                    continue

                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                if start_dt > cutoff:
                    continue

                if is_likely_adult_event(min_age):
                    continue

                ages = extract_ages(age_desc or "")
                month = start_dt.strftime("%b")
                day = str(start_dt.day)
                year = str(start_dt.year)

                # Build categories from title + program type
                title_lower = name.lower()
                keyword_tags = [tag for keyword, tag in TITLE_KEYWORD_TO_CATEGORY.items() if keyword in title_lower]
                keyword_category_str = ", ".join(keyword_tags)

                program_type_categories = ""
                if category == "Fitness & Wellness":
                    program_type_categories = "Event Location - Virginia Beach, List - Fitness Events"

                categories = ", ".join(filter(None, [program_type_categories, keyword_category_str]))

                events.append({
                    "Event Name": f"{name} (Virginia Beach)",
                    "Event Link": link,
                    "Event Status": status,
                    "Time": time,
                    "Ages": ages,
                    "Location": site,
                    "Month": month,
                    "Day": day,
                    "Year": year,
                    "Event Date": start_date,
                    "Event End Date": end_date,
                    "Event Description": desc,
                    "Series": "",
                    "Program Type": category,
                    "Categories": categories
                })

            except Exception as e:
                print(f"⚠️ Error processing item: {e}")

    print(f"✅ Scraped {len(events)} events from VBPR.")
    return events
