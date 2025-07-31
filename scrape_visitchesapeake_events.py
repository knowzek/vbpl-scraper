from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import re
import json
from constants import TITLE_KEYWORD_TO_CATEGORY, UNWANTED_TITLE_KEYWORDS

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
    print("\U0001f33e Scraping Visit Chesapeake events via Playwright...")

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
        page.goto("https://www.visitchesapeake.com/events", timeout=60000)

        print("\U0001f4dc Scrolling page to load all events...")
        prev_height = 0
        while True:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)
            curr_height = page.evaluate("document.body.scrollHeight")
            if curr_height == prev_height:
                break
            prev_height = curr_height

        # 🔍 Dump the full rendered page content for debugging
        # Wait for base event cards to appear
        page.wait_for_load_state("networkidle")

        
        # Scroll the page fully to trigger hydration
        print("📜 Scrolling page to load all events...")
        prev_height = 0
        while True:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)
            curr_height = page.evaluate("document.body.scrollHeight")
            if curr_height == prev_height:
                break
            prev_height = curr_height
        
        # Wait for JS to hydrate internal content like .actions
        try:
            page.wait_for_selector("div.shared-item div.actions", timeout=8000)
        except:
            print("⚠️ Timeout: .actions divs never appeared.")
        
        # Re-select hydrated cards
        cards = page.query_selector_all("div.shared-item[data-type='event']")
        print(f"🔍 Found {len(cards)} hydrated event cards")


        print(f"🔍 Found {len(cards)} event cards")
        for card in cards:
            print("🔍 Inspecting card HTML snippet:")
            print(card.inner_html()[:600])

            try:
                # skip if data attributes not present
                title_el = card.query_selector("div.contents h2 a")
                if not title_el:
                    continue
                
                name = title_el.inner_text().strip()
                if not name or name in seen:
                    continue
                seen.add(name)
                
                link = title_el.get_attribute("href")
                if link:
                    link = "https://www.visitchesapeake.com" + link
                
                date_el = card.query_selector("p.dates")
                if not date_el:
                    continue
                date_text = date_el.inner_text().strip()
                try:
                    start_dt = datetime.strptime(date_text, "%B %d, %Y")
                except:
                    continue
                
                if start_dt < today or start_dt > cutoff:
                    print(f"🧾 Passing event → {name} on {start_dt.strftime('%Y-%m-%d')}")

                    continue
                
                location_el = card.query_selector("p.address")
                location = location_el.inner_text().strip() if location_el else ""
                
                desc = ""  # no clear desc available

                text_to_match = name.lower()

                ages = extract_ages(text_to_match)

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
                print(f"⚠️ Error processing card: {e}")

        browser.close()

    print(f"✅ Scraped {len(events)} Visit Chesapeake events.")
    return events
