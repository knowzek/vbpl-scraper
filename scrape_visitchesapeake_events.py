from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from constants import TITLE_KEYWORD_TO_CATEGORY, UNWANTED_TITLE_KEYWORDS
from config import map_age_to_categories
import re

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
    print("🌾 Scraping Visit Chesapeake events via Playwright...")

    today = datetime.now()
    if mode == "weekly":
        cutoff = today + timedelta(days=7)
    elif mode == "monthly":
        cutoff = today + timedelta(days=31)
    else:
        cutoff = today + timedelta(days=90)

    events = []
    seen = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.visitchesapeake.com/events/?categoryid=1016", timeout=60000)
        print("📜 Scrolling page to load all events...")

        prev_height = 0
        while True:
            page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)
            curr_height = page.evaluate("document.body.scrollHeight")
            if curr_height == prev_height:
                break
            prev_height = curr_height

        content = page.content()
        soup = BeautifulSoup(content, "html.parser")
        cards = soup.select("li.event_listing")

        for card in cards:
            try:
                title_elem = card.select_one(".title a")
                name = title_elem.get_text(strip=True)
                link = "https://www.visitchesapeake.com" + title_elem.get("href", "")
                if name in seen:
                    continue
                seen.add(name)

                # Skip if marked as recurring
                if "Recurring" in name or "recurring" in name:
                    print(f"⏭️ Skipping recurring series: {name}")
                    continue

                date_elem = card.select_one(".date")
                if not date_elem:
                    continue
                raw_date = date_elem.get_text(strip=True)
                try:
                    start_dt = datetime.strptime(raw_date, "%B %d, %Y")
                except:
                    print(f"⚠️ Skipping invalid date: {raw_date}")
                    continue

                if start_dt < today or start_dt > cutoff:
                    continue

                desc_elem = card.select_one(".description")
                desc_html = desc_elem.decode_contents() if desc_elem else ""
                desc = BeautifulSoup(desc_html, "html.parser").get_text(" ", strip=True)

                location_elem = card.select_one(".location")
                location = location_elem.get_text(strip=True) if location_elem else "Chesapeake"

                full_text = f"{name} {desc}".lower()
                if any(kw in full_text for kw in UNWANTED_TITLE_KEYWORDS):
                    continue

                keyword_tags = []
                for keyword, tag_string in TITLE_KEYWORD_TO_CATEGORY.items():
                    if keyword.lower() in full_text:
                        keyword_tags.extend(tag_string.split(","))
                keyword_category_str = ", ".join(sorted(set(keyword_tags)))
                ages = extract_ages(full_text)
                age_tags = map_age_to_categories(0, 0)  # Default fallback, customize if needed

                categories = ", ".join(filter(None, [
                    "Event Location - Chesapeake",
                    "Audience - Free Event",
                    keyword_category_str,
                    ages
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
                print(f"⚠️ Error parsing card: {e}")

        browser.close()

    print(f"✅ Scraped {len(events)} Visit Chesapeake events.")
    return events
