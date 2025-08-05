import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from constants import TITLE_KEYWORD_TO_CATEGORY
from config import map_age_to_categories
from constants import UNWANTED_TITLE_KEYWORDS
import re

def is_likely_adult_event(min_age, max_age):
    return min_age >= 18 and (max_age == 0 or max_age >= 18)


def extract_ages(text):
    text = text.lower()
    matches = set()

    if any(kw in text for kw in ["infants", "babies", "baby", "toddlers", "toddler", "0-2"]):
        matches.add("Infant")
    if any(kw in text for kw in ["age 3", "ages 3", "ages 4", "preschool", "age 4"]):
        matches.add("Preschool")

    teen_keywords = [
        "grades 6-12", "grades 6 through 12", "grades 6", "grades 7", "grades 8", 
        "grades 9", "grades 10", "grades 11", "grades 12", "teens", "high school", "teen", "teens", "middle school"
    ]
    school_age_keywords = [
        "school age", "elementary", "grades 1-5", "grades 1 through 5", "grades 1", "grades 2", 
        "grades 3", "grades 4", "grades 5", "ages 5-10", "ages 5", "ages 6", "ages 7", "ages 8", 
        "ages 9", "ages 10", "ages 11", "ages 12", "ages 5-12"
    ]

    if any(kw in text for kw in teen_keywords):
        matches.add("Teens")
    elif any(kw in text for kw in school_age_keywords):
        matches.add("School Age")

    if "all ages" in text:
        matches.add("All Ages")

    return ", ".join(sorted(matches))



def scrape_vbpr_events(mode="all"):
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


    if mode == "weekly":
        cutoff = today + timedelta(days=7)
    elif mode == "monthly":
        cutoff = today + timedelta(days=31)
    else:
        cutoff = today + timedelta(days=90)

    print("🎯 Scraping VBPR events via ActiveNet JSON API...")
    print(f"🧪 VBPR scrape starting with mode={mode}")
    print(f"📆 Today is {today.strftime('%Y-%m-%d')}")
    print(f"📆 Cutoff is {cutoff.strftime('%Y-%m-%d')}")

    date_start = today.strftime("%Y-%m-%d")
    date_end = cutoff.strftime("%Y-%m-%d")

    events = []
    page_number = 1
    seen = set()
    empty_pages = 0
    MAX_EMPTY_PAGES = 15

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
            print(f"⚠️ Returning {len(events)} events scraped before error.")
            return events  # <—— Prevent total loss

        body = data.get("body")
        if not isinstance(body, dict):
            print(f"⚠️ Unexpected body format on page {page_number}: {type(body)}")
            break
        
        items = body.get("activity_items", [])
        print(f"📦 Page {page_number} contains {len(items)} items")

        if not items:
            empty_pages += 1
            print(f"🚫 Page {page_number} had no items (empty_pages={empty_pages})")
            if empty_pages >= MAX_EMPTY_PAGES:
                print("🛑 Max empty page threshold reached.")
                break

            else:
                page_number += 1
                continue  # ✅ Skip processing the empty page
        else:
            empty_pages = 0

        in_range_found = False  # Track whether any events on this page are in range
        for item in items:
            
            try:
                name = item.get("name", "").strip()
                if not name or name in seen:
                    continue
                event_id = item.get("detail_url", "")
                if not event_id or event_id in seen:
                    continue
                seen.add(event_id)


                desc_html = item.get("desc", "")
                desc_html = desc_html.replace("<br>", "\n").replace("<br/>", "\n").replace("</p>", "\n")
                desc = BeautifulSoup(desc_html, "html.parser").get_text().strip()

                # 👇 Skip events based on unwanted keywords
                text_to_match = (name + " " + desc).lower()
                if any(bad_kw.lower() in text_to_match for bad_kw in UNWANTED_TITLE_KEYWORDS):
                    print(f"⏭️ Skipping unwanted keyword match: {name}")
                    continue
                    
                status = item.get("urgent_message", {}).get("status_description", "Available")
                start = item.get("date_range_start", "")
                end = item.get("date_range_end", "")
                
                # 🧹 Filter out recurring/multi-day events
                if end.strip() and start != end:
                    print(f"⏭️ Skipping recurring/multi-day event: {name} ({start} to {end})")
                    continue

                time = item.get("time_range_landing_page", "") or item.get("time_range", "")
                site = item.get("site", "").strip()
                link = item.get("detail_url", "").strip()
                category = item.get("category", "").strip()
                age_text = item.get("age_description", "") or ""
                # Attempt to extract numeric min/max age from age_text
                min_age, max_age = 0, 0
                age_text_clean = age_text.lower()
                
                # Pattern: "at least 6 yrs but less than 12 yrs"
                match = re.search(r'at least (\d+)[^\d]+less than (\d+)', age_text_clean)
                if match:
                    min_age = int(match.group(1))
                    max_age = int(match.group(2)) - 1  # treat "less than" as exclusive
                else:
                    # Pattern: "6 yrs +"
                    match = re.search(r'(\d+)\s*yrs?\s*\+', age_text_clean)
                    if match:
                        min_age = int(match.group(1))
                        max_age = 0  # open-ended
                    else:
                        # Pattern: "ages 5-12" or "5 to 12"
                        match = re.search(r'(\d+)[^\d]+(\d+)', age_text_clean)
                        if match:
                            min_age = int(match.group(1))
                            max_age = int(match.group(2))

                age_based_categories = map_age_to_categories(min_age, max_age)
                fee_data = item.get("fee", {})
                fee_display = fee_data.get("label", "").strip()


                if not start:
                    continue

                start_dt = datetime.strptime(start, "%Y-%m-%d")
                if start_dt < today or start_dt > cutoff:
                    print(f"📆 Skipping: {name} → {start_dt.strftime('%Y-%m-%d')} is outside range {today.strftime('%Y-%m-%d')} to {cutoff.strftime('%Y-%m-%d')}")
                    continue
                else:
                    in_range_found = True

                print(f"🧪 Evaluating: {name}")
                print(f"   Fee: {fee_display}, Start: {start}, End: {end}")
                
                if is_likely_adult_event(min_age, max_age):
                    print(f"⏭️ Skipping due to adult-only age range: {min_age}-{max_age}")
                    continue


                # 🧠 NEW: Skip events that are not free AND are multi-day
                cost_text = fee_display.lower().strip()
                is_free = any(
                    phrase in cost_text
                    for phrase in ["free", "$0", "no additional fee", "no fee", "no cost"]
                )
                print(f"🎟️ {name} → Fee Label: '{fee_display}' → Is Free? {is_free}")    
                if age_text.strip():
                    ages = age_text.strip()
                else:
                    ages = ""

                # 👇 Search both title and description for keyword matches
                text_to_match = (name + " " + desc).lower()
                
                keyword_tags = []
                for keyword, tag_string in TITLE_KEYWORD_TO_CATEGORY.items():
                
                    pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
                    if re.search(pattern, text_to_match):

                        tags = [t.strip() for t in tag_string.split(",")]
                        keyword_tags.extend(tags)
                
                if keyword_tags:
                    print(f"🧠 Matched keywords in '{name}': {keyword_tags}")
                
                keyword_category_str = ", ".join(sorted(set(keyword_tags)))

                program_type_categories = ""
                if category == "Fitness & Wellness":
                    program_type_categories = "Event Location - Virginia Beach, List - Fitness Events"

                free_event_tag = "Audience - Free Event" if is_free else ""
                base_location_tag = "Event Location - Virginia Beach"
                print(f"📍 base_location_tag: {base_location_tag}")
                print(f"🎟️ free_event_tag: {free_event_tag}")
                print(f"🏷️ keyword_category_str: {keyword_category_str}")
                print(f"👶 age_based_categories: {age_based_categories}")

                categories = ", ".join(filter(None, [
                    base_location_tag,
                    program_type_categories,
                    keyword_category_str,
                    age_based_categories,
                    free_event_tag
                ]))

                print(f"✅ Keeping: {name}")
                print(f"🆗 Final Event: {name} → {start} {fee_display} {link}")

                events.append({
                    "Event Name": name,
                    "Event Link": link,
                    "Event Status": status,
                    "Time": time,
                    "Ages": ages,
                    "Location": site,
                    "Month": start_dt.strftime("%b"),
                    "Day": str(start_dt.day),
                    "Year": str(start_dt.year),
                    "Event Description": desc,
                    "Series": "",
                    "Program Type": category,
                    "Categories": categories  # only include this if your shared logic expects it
                })
                if len(events[-1]) > 13:
                    print("⚠️ WARNING: Too many columns in VBPR event row!", events[-1])

            except Exception as e:
                print(f"⚠️ Error parsing item: {e}")
        # End of your for-loop processing all items on the current page...
        
        MAX_PAGES = 1000
        if page_number > MAX_PAGES:
            print("🛑 Max page limit reached.")
            break

        page_number += 1

    print(f"✅ Scraped {len(events)} VBPR events.")
    return events
