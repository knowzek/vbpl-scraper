import requests
from datetime import datetime, timedelta
from constants import TITLE_KEYWORD_TO_CATEGORY, UNWANTED_TITLE_KEYWORDS
from bs4 import BeautifulSoup

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
    print("🌾 Scraping Visit Chesapeake events...")

    today = datetime.now()
    if mode == "weekly":
        cutoff = today + timedelta(days=7)
    elif mode == "monthly":
        cutoff = today + timedelta(days=31)
    else:
        cutoff = today + timedelta(days=90)

    base_url = "https://www.visitchesapeake.com/events/"
    api_url = "https://www.visitchesapeake.com/includes/functions_ajax.cfm"

    start_date = today.strftime("%m/%d/%Y")
    end_date = cutoff.strftime("%m/%d/%Y")

    params = {
        "skip": 0,
        "categoryid": 1016,
        "startDate": start_date,
        "endDate": end_date,
        "sort": "date"
    }

    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0"
    }

    events = []
    seen = set()

    while True:
        try:
            res = requests.get("https://www.visitchesapeake.com/includes/functions_ajax.cfm", params=params, headers=headers, timeout=30)
            res.raise_for_status()
            json_data = res.json()

            docs = json_data.get("docs", [])
            if not docs:
                break

            for item in docs:
                if item.get("typeName") != "One-Time Event":
                    continue
                categories = [c.get("catName", "") for c in item.get("categories", [])]
                if "Family Fun" not in categories:
                    continue

                name = item.get("title", "").strip()
                if name in seen:
                    continue
                seen.add(name)

                desc = item.get("teaser", "").strip()
                full_desc = item.get("description", "") or ""
                description = desc or full_desc

                if any(kw.lower() in (name + " " + description).lower() for kw in UNWANTED_TITLE_KEYWORDS):
                    continue

                start = item.get("startDate")
                end = item.get("endDate") or start
                time_str = ""  # Optional — can infer if needed
                location = item.get("location", item.get("address1", "")).strip()
                event_link = item.get("absoluteUrl", "").strip()
                ages = extract_ages(name + " " + description)

                try:
                    start_dt = datetime.strptime(start[:10], "%Y-%m-%d")
                except:
                    continue

                if start_dt > cutoff:
                    continue

                keyword_tags = []
                text_to_match = (name + " " + description).lower()
                for keyword, tag_string in TITLE_KEYWORD_TO_CATEGORY.items():
                    if keyword.lower() in text_to_match:
                        keyword_tags.extend(tag_string.split(", "))

                categories = ", ".join(sorted(set(["Event Location - Chesapeake", "Audience - Free Event"] + keyword_tags)))

                events.append({
                    "Event Name": f"{name} (Chesapeake)",
                    "Event Link": event_link,
                    "Event Status": "Available",
                    "Time": time_str,
                    "Ages": ages,
                    "Location": location,
                    "Month": start_dt.strftime("%b"),
                    "Day": str(start_dt.day),
                    "Year": str(start_dt.year),
                    "Event Description": description,
                    "Series": "",
                    "Program Type": "Family Fun",
                    "Categories": categories
                })

            params["skip"] += len(docs)

        except Exception as e:
            print(f"❌ Error: {e}")
            break

    print(f"✅ Scraped {len(events)} Visit Chesapeake events.")
    return events
