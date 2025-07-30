
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from constants import TITLE_KEYWORD_TO_CATEGORY

def is_likely_adult_event(min_age, max_age):
    return min_age == 18 and (max_age == 0 or max_age >= 18)


def extract_ages(text):
    text = text.lower()
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
    print("🎯 Scraping VBPR events via ActiveNet JSON API...")

    today = datetime.today()
    if mode == "weekly":
        cutoff = today + timedelta(days=7)
    elif mode == "monthly":
        cutoff = today + timedelta(days=31)
    else:
        cutoff = today + timedelta(days=90)

    date_start = today.strftime("%Y-%m-%d")
    date_end = cutoff.strftime("%Y-%m-%d")

    events = []
    page_number = 1
    seen = set()

    while True:
        print(f"📄 Fetching page {page_number}...")
        url = "https://anc.apm.activecommunities.com/vbparksrec/rest/activities/list"
        headers = {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://anc.apm.activecommunities.com/vbparksrec/activity/search?activity_select_param=2&viewMode=list",
            "User-Agent": "Mozilla/5.0"
        }
        payload = {
            "activity_select_param": 2,
            "viewMode": "list",
            "locale": "en-US",
            "page_number": page_number,
            "search_text": "",
            "date_start": date_start,
            "date_end": date_end,
            "activity_tag": "",
            "activity_type": [],
            "age_group": [],
            "location": [],
            "time": [],
            "day": [],
            "sort_field": "Relevance"
        }

        try:
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            print(f"❌ Error on page {page_number}: {e}")
            print("🪵 Raw response text:")
            print(res.text[:1000])
            break

        items = data.get("body", {}).get("activity_items", [])
        if not items:
            print("🚫 No more items.")
            break

        for item in items:
            try:
                name = item.get("name", "").strip()
                if not name or name in seen:
                    continue
                seen.add(name)

                desc_html = item.get("desc", "")
                desc = BeautifulSoup(desc_html, "html.parser").get_text().strip()
                status = item.get("urgent_message", {}).get("status_description", "Available")
                start = item.get("date_range_start", "")
                end = item.get("date_range_end", "")
                time = item.get("time_range_landing_page", "") or item.get("time_range", "")
                site = item.get("site", "").strip()
                link = "https://anc.apm.activecommunities.com" + (item.get("detail_url", "") or "")
                category = item.get("category", "").strip()
                age_text = item.get("age_description", "") or ""
                min_age = item.get("age_min_year", 0)
                max_age = item.get("age_max_year", 0)
                fee_display = item.get("fee_display", "") or ""

                if not start:
                    continue

                start_dt = datetime.strptime(start, "%Y-%m-%d")
                if start_dt < today or start_dt > cutoff:
                    print(f"📆 Skipping: {name} → {start_dt.strftime('%Y-%m-%d')} is outside range {today.strftime('%Y-%m-%d')} to {cutoff.strftime('%Y-%m-%d')}")
                    continue
                
                print(f"🧪 Evaluating: {name}")
                print(f"   Fee: {fee_display}, Start: {start}, End: {end}")
                
                if is_likely_adult_event(min_age, max_age):
                    print(f"⏭️ Skipping due to adult-only age range: {min_age}-{max_age}")
                    continue


                # 🧠 NEW: Skip events that are not free AND are multi-day
                cost_text = fee_display.lower()
                is_free = any(phrase in cost_text for phrase in ["free", "$0", "no additional fee"])
                is_single_day = start == end

                # 🧠 Skip if the event is both: not free AND multi-day
                if not is_free and not is_single_day:
                    print("⏭️ Skipping due to cost/duration filter")
                    continue

                ages = extract_ages(age_text + " " + desc + " " + name)
                title_lower = name.lower()
                keyword_tags = [tag for keyword, tag in TITLE_KEYWORD_TO_CATEGORY.items() if keyword in title_lower]
                keyword_category_str = ", ".join(keyword_tags)

                program_type_categories = ""
                if category == "Fitness & Wellness":
                    program_type_categories = "Event Location - Virginia Beach, List - Fitness Events"

                categories = ", ".join(filter(None, [program_type_categories, keyword_category_str]))
                print(f"✅ Keeping: {name}")

                events.append({
                    "Event Name": f"{name} (Virginia Beach)",
                    "Event Link": link,
                    "Event Status": status,
                    "Time": time,
                    "Ages": ages,
                    "Location": site,
                    "Month": start_dt.strftime("%b"),
                    "Day": str(start_dt.day),
                    "Year": str(start_dt.year),
                    "Event Date": start,
                    "Event End Date": end,
                    "Event Description": desc,
                    "Series": "",
                    "Program Type": category,
                    "Categories": categories
                })

            except Exception as e:
                print(f"⚠️ Error parsing item: {e}")

        page_number += 1

    print(f"✅ Scraped {len(events)} VBPR events.")
    return events
