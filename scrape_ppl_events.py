from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
from playwright.sync_api import sync_playwright
from constants import LIBRARY_CONSTANTS

BASE_URL = "https://www.portsmouthpubliclibrary.org/calendar.aspx?CID=24"

def is_likely_adult_event(text):
    text = text.lower()
    keywords = [
        "adult", "18+", "21+", "resume", "medicare", "investment",
        "retirement", "social security", "veterans", "seniors",
        "tax help", "finance", "job help", "knitting"
    ]
    return any(kw in text for kw in keywords)

def extract_ages(text):
    text = text.lower()
    matches = set()
    if any(kw in text for kw in ["infants", "babies", "baby", "0-2"]):
        matches.add("Infant")
    if any(kw in text for kw in ["toddlers", "2-3", "2 and 3", "age 2", "age 3", "preschool"]):
        matches.add("Preschool")
    if any(kw in text for kw in ["school age", "elementary", "5-8", "ages 5", "grade"]):
        matches.add("School Age")
    if any(kw in text for kw in ["tween", "tweens", "middle school"]):
        matches.add("Tweens")
    if any(kw in text for kw in ["teen", "teens", "high school"]):
        matches.add("Teens")
    if "all ages" in text:
        matches.add("All Ages")
    return ", ".join(sorted(matches))

def scrape_ppl_events(mode="all"):
    print("🧭 Launching Playwright for Portsmouth scrape...")

    today = datetime.now()
    if mode == "weekly":
        start_date = today
        end_date = today + timedelta(days=7)
    elif mode == "monthly":
        start_date = datetime(today.year, today.month, 1)
        if today.month == 12:
            end_date = datetime(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(today.year, today.month + 1, 1) - timedelta(days=1)
    else:
        start_date = today
        end_date = today + timedelta(days=90)

    events = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto(BASE_URL, timeout=30000)
        page.wait_for_selector(".event-title", timeout=15000)

        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        event_blocks = soup.select(".calendar a[href*='EID=']")

        for block in event_blocks:
            try:
                title = block.get_text(strip=True)
                url = "https://www.portsmouthpubliclibrary.org" + block["href"]
                parent = block.find_parent("td")

                date_el = parent.find_previous("tr").find("th")
                if not date_el:
                    continue

                date_str = date_el.get_text(strip=True)
                try:
                    dt = datetime.strptime(date_str, "%A, %B %d, %Y")
                except Exception:
                    continue

                if dt < start_date or dt > end_date:
                    continue

                detail_page = context.new_page()
                detail_page.goto(url, timeout=15000)
                detail_html = detail_page.content()
                detail_soup = BeautifulSoup(detail_html, "html.parser")

                desc_tag = detail_soup.select_one(".calendarDetail")
                desc = desc_tag.get_text(strip=True) if desc_tag else ""

                time_match = re.search(r"Time:\s*(.*)", desc, re.IGNORECASE)
                time_str = time_match.group(1).strip() if time_match else ""

                loc_match = re.search(r"Location:\s*(.*)", desc, re.IGNORECASE)
                raw_location = loc_match.group(1).strip() if loc_match else "Portsmouth Public Library"

                if is_likely_adult_event(title) or is_likely_adult_event(desc):
                    print(f"⏭️ Skipping: Adult event → {title}")
                    continue

                ages = extract_ages(title + " " + desc)

                events.append({
                    "Event Name": title,
                    "Event Link": url,
                    "Event Status": "Available",
                    "Time": time_str,
                    "Ages": ages,
                    "Location": raw_location,
                    "Month": dt.strftime("%b"),
                    "Day": str(dt.day),
                    "Year": str(dt.year),
                    "Event Date": dt.strftime("%Y-%m-%d"),
                    "Event End Date": dt.strftime("%Y-%m-%d"),
                    "Event Description": desc,
                    "Series": "",
                    "Program Type": "",
                    "Categories": ""
                })

                detail_page.close()

            except Exception as e:
                print(f"⚠️ Error parsing event: {e}")

        browser.close()

    print(f"✅ Scraped {len(events)} events from Portsmouth Public Library.")
    return events
