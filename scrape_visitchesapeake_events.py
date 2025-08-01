from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re

def sentence_case(title):
    cleaned = title.strip().lower()
    return re.sub(r'(^\w)|(?<=[\.!\?]\s)(\w)', lambda m: m.group().upper(), cleaned)

def scrape_visitchesapeake_events(mode="monthly"):
    print("🌾 Scraping Visit Chesapeake events with Playwright...")

    cutoff = datetime.now() + timedelta(days=31 if mode == "monthly" else 90)
    base_url = "https://www.visitchesapeake.com/events/"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # use headless=False for debugging
        page = browser.new_page()
        page.goto(base_url, timeout=60000)
        page.set_viewport_size({"width": 1280, "height": 800})
        page.screenshot(path="render_debug.png", full_page=True)
        print("📸 Screenshot saved — check render_debug.png")
        
        print("📄 Page loaded. Waiting for event cards to render...")
        page.wait_for_selector("div.shared-item.item[data-type='event']", timeout=60000, state="attached")
        print("✅ Event cards found. Parsing...")


        # Wait for events to render
        print("📄 Page loaded. Waiting for event cards to render...")
        page.wait_for_selector("div.shared-item.item[data-type='event']", timeout=60000, state="attached")


        print("✅ Event cards found. Parsing HTML...")

        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        cards = soup.select("div.shared-item.item[data-type='event']")
        print(f"🔍 Found {len(cards)} event cards")

        events = []
        seen = set()

        for card in cards:
            try:
                title_el = card.select_one("div.contents h2 a")
                if not title_el:
                    continue
                name = sentence_case(title_el.text.strip())
                if name in seen:
                    continue
                seen.add(name)
                print("🔍 Parsing event card...")
                print(f"📌 Event: {name}")

                href = title_el.get("href", "")
                link = "https://www.visitchesapeake.com" + href if href.startswith("/") else href

                date_el = card.select_one("p.dates")
                date_text = date_el.text.strip() if date_el else ""
                if "–" in date_text or "to" in date_text.lower():
                    print(f"🔁 Skipping series: {name}")
                    continue

                try:
                    start_dt = datetime.strptime(date_text, "%B %d, %Y")
                    if start_dt > cutoff:
                        continue
                except Exception as e:
                    print(f"⚠️ Date parse error for {name}: {e}")
                    continue

                location_el = card.select_one("p.address")
                location = location_el.get_text(strip=True) if location_el else ""
                print(f"🗓️ Date: {start_dt.strftime('%Y-%m-%d')} | Location: {location}")
                events.append({
                    "Event Name": name,
                    "Event Link": link,
                    "Event Status": "Available",
                    "Time": "",
                    "Ages": "",
                    "Location": location,
                    "Month": start_dt.strftime("%b"),
                    "Day": str(start_dt.day),
                    "Year": str(start_dt.year),
                    "Event Description": "See event link for details",
                    "Series": "",
                    "Program Type": "Family Fun",
                    "Categories": "Event Location - Chesapeake, Audience - Free Event, Audience - Family Event"
                })
                print(f"✅ Added event: {name}")
            except Exception as e:
                print(f"⚠️ Error parsing event: {e}")

        browser.close()

    print(f"✅ Scraped {len(events)} events.")
    return events

if __name__ == "__main__":
    scrape_visitchesapeake_events()
