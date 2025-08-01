import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
from constants import TITLE_KEYWORD_TO_CATEGORY
from export_to_csv import send_notification_email_with_attachment


def sentence_case(title):
    cleaned = title.strip().lower()
    return re.sub(r'(^\w)|(?<=[\.!\?]\s)(\w)', lambda m: m.group().upper(), cleaned)


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
    print("🌾 Scraping Visit Chesapeake events (static HTML)...")

    cutoff = datetime.now() + timedelta(days=7 if mode == "weekly" else 31 if mode == "monthly" else 90)
    base_url = "https://www.visitchesapeake.com"
    response = requests.get(f"{base_url}/events")
    soup = BeautifulSoup(response.text, "html.parser")

    cards = soup.select("div.shared-item.item[data-type='event']")
    print(f"🔍 Found {len(cards)} event cards")

    events = []
    seen = set()

    for card in cards:
        try:
            title_el = card.select_one("div.contents h2 a")
            if not title_el:
                print("⚠️ Skipping card — no title/link found")
                continue

            name = sentence_case(title_el.text.strip())
            if name in seen:
                continue
            seen.add(name)

            href = title_el.get("href", "")
            if not href.startswith("/event/"):
                print(f"⚠️ Skipping {name}: invalid href")
                continue
            link = base_url + href

            date_el = card.select_one("p.dates")
            if not date_el:
                print(f"⚠️ Skipping {name}: no date element")
                continue
            date_text = date_el.text.strip()
            if "–" in date_text or "to" in date_text.lower():
                print(f"🔁 Skipping possible series: {name}")
                continue

            try:
                start_dt = datetime.strptime(date_text, "%B %d, %Y")
                if start_dt > cutoff:
                    continue
            except Exception as e:
                print(f"⚠️ Date parse failed for {name}: {e}")
                continue

            location_el = card.select_one("p.address")
            location = location_el.get_text(strip=True) if location_el else ""

            # Visit detail page for full description
            detail_res = requests.get(link)
            detail_soup = BeautifulSoup(detail_res.text, "html.parser")
            desc_el = detail_soup.select_one("div.description")
            desc = desc_el.get_text(strip=True) if desc_el else "See event link for details"

            text_to_match = f"{name} {desc}".lower()
            ages = extract_ages(text_to_match)

            keyword_tags = []
            for keyword, tag_string in TITLE_KEYWORD_TO_CATEGORY.items():
                if re.search(rf"\b{re.escape(keyword.lower())}\b", text_to_match):
                    keyword_tags.extend(tag_string.split(","))

            keyword_category_str = ", ".join(sorted(set(keyword_tags)))
            categories = ", ".join(filter(None, [
                "Event Location - Chesapeake",
                "Audience - Free Event",
                "Audience - Family Event",
                keyword_category_str
            ]))

            events.append({
                "Event Name": name,
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
            print(f"⚠️ Error processing event: {e}")

    print(f"✅ Scraped {len(events)} events.")

    return events
