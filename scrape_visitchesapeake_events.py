from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import re
import json
from constants import TITLE_KEYWORD_TO_CATEGORY, UNWANTED_TITLE_KEYWORDS

def sentence_case(title):
    cleaned = title.strip().lower()
    return re.sub(r'(^\w)|(?<=[\.\!\?]\s)(\w)', lambda m: m.group().upper(), cleaned)


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
            
        # ✅ Ensure hydration of all dynamically loaded cards
        print("⏳ Waiting for hydrated titles to appear...")
        try:
            page.wait_for_selector("div.shared-item.item div.contents h2 a", timeout=10000)
            print("✅ Hydrated event titles are now present.")
        except:
            print("⚠️ Timeout waiting for hydrated event titles.")

        # 🔍 Dump the full rendered page content for debugging
        # Wait for base event cards to appear
        # Wait for base load
        page.wait_for_load_state("load")
        
        # Safer: wait until event cards are present in DOM (but not necessarily visible)
        try:
            page.wait_for_selector("div.shared-item[data-type='event']", timeout=10000, state="attached")
            print("✅ Found event cards in DOM.")
        except:
            print("❌ Failed to find event cards — page may not have loaded properly.")
            return []
        
        # Wait for JS to hydrate internal content like .actions
        try:
            page.wait_for_selector("div.shared-item div.actions", timeout=8000)
        except:
            print("⚠️ Timeout: .actions divs never appeared.")

        # ✅ Dump full HTML for debugging
        html = page.content()
        with open("chesapeake_debug.html", "w", encoding="utf-8") as f:
            f.write(html)
        # Re-select hydrated cards
        cards = page.query_selector_all("div.shared-item[data-type='event']")
        print(f"🔍 Found {len(cards)} hydrated event cards")

        print(f"🔍 Found {len(cards)} event cards")
        for card in cards:
            print("🔍 Inspecting card HTML snippet:")
            print(card.inner_html()[:600])
        
            try:
                print("🔍 Inspecting full card HTML:")
                print(card.inner_html())
                # Extract title from <h2>
                title_el = card.query_selector("h2")
                if not title_el:
                    print("⚠️ Skipping card — no title found")
                    continue
                name = title_el.inner_text().strip()
                if not name or name in seen:
                    continue
                seen.add(name)
                name = sentence_case(name)
                
                # ✅ FIX: Get href from the card (the outer <a>)
                link_el = card.query_selector("h2 a")
                if not link_el:
                    print(f"⚠️ Skipping {name}: link element not found")
                    continue
                link = link_el.get_attribute("href")

                if not link or not link.startswith("/event/"):
                    print(f"⚠️ Skipping {name}: missing or invalid href")
                    continue
                link = "https://www.visitchesapeake.com" + link

        
                date_el = card.query_selector("p.dates")
                if not date_el:
                    print(f"⚠️ Skipping {name}: no date element")
                    continue
                date_text = date_el.inner_text().strip()
        
                if "–" in date_text or "to" in date_text.lower():
                    print(f"🔁 Skipping possible series: {name}")
                    continue
        
                try:
                    start_dt = datetime.strptime(date_text, "%B %d, %Y")
                except Exception as e:
                    print(f"⚠️ Date parse failed for {name}: {e}")
                    continue
        
                detail_page = browser.new_page()
                try:
                    detail_page.goto(link, timeout=30000)
                    desc_el = detail_page.query_selector("div.description")
                    desc = desc_el.inner_text().strip() if desc_el else "See event link for details"
                finally:
                    detail_page.close()
        
                location_el = card.query_selector("p.address")
                location = location_el.inner_text().strip() if location_el else ""
        
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
                print(f"⚠️ Error processing card: {e}")
    

        browser.close()

    print(f"✅ Scraped {len(events)} Visit Chesapeake events.")
    from export_to_csv import send_notification_email_with_attachment

    send_notification_email_with_attachment(
        file_path="/opt/render/project/src/chesapeake_debug.html",
        subject="Chesapeake Debug HTML",
        recipient="knowzek@gmail.com"  # ⬅️ Replace this with your actual email
    )

    return events
