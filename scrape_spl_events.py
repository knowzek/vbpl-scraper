from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
from playwright.sync_api import sync_playwright

BASE_URL = "https://suffolkpubliclibrary.libcal.com/calendar"

def is_likely_adult_event(text):
    text = text.lower()
    keywords = [
        "adult", "18+", "21+", "job help", "resume", "medicare",
        "investment", "retirement", "social security", "veterans",
        "seniors", "tax help", "real estate", "finance", "knitting"
    ]
    return any(kw in text for kw in keywords)

def extract_ages(text):
    text = text.lower()
    matches = set()
    if any(kw in text for kw in ["infants", "babies", "baby", "0-2"]):
        matches.add("Infant")
    if any(kw in text for kw in ["toddlers", "2-3", "2 and 3", "age 2", "age 3"]):
        matches.add("Preschool")
    if any(kw in text for kw in ["preschool", "3-5", "ages 3-5"]):
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

def scrape_spl_events(mode="all"):
    print("🧭 Launching Playwright for SPL scrape...")

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
        page.wait_for_selector(".s-lc-c-evt", timeout=15000)

        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        event_listings = soup.find_all("div", class_="media s-lc-c-evt")

        for listing in event_listings:
            try:
                title_tag = listing.find("h3", class_="media-heading")
                title = title_tag.get_text(strip=True) if title_tag else "Untitled Event"
                url_tag = title_tag.find("a") if title_tag else None
                url = url_tag["href"] if url_tag and url_tag.has_attr("href") else ""

                desc_tag = listing.find("div", class_="s-lc-c-evt-des")
                desc = desc_tag.get_text(strip=True) if desc_tag else ""

                dl = listing.find("dl", class_="dl-horizontal")
                info = {}
                if dl:
                    for dt_tag in dl.find_all("dt"):
                        key = dt_tag.get_text(strip=True).rstrip(":").lower()
                        dd_tag = dt_tag.find_next_sibling("dd")
                        if dd_tag:
                            info[key] = dd_tag.get_text(strip=True)

                date_text = info.get("date", "")
                try:
                    dt = datetime.strptime(date_text, "%A, %B %d, %Y")
                except Exception:
                    continue

                if dt < start_date or dt > end_date:
                    continue

                if is_likely_adult_event(title) or is_likely_adult_event(desc):
                    continue

                time_str = info.get("time", "")
                location = info.get("location", "Suffolk Public Library")
                ages = extract_ages(title + " " + desc)

                events.append({
                    "Event Name": title,
                    "Event Link": url,
                    "Event Status": "Available",
                    "Time": time_str,
                    "Ages": ages,
                    "Location": location,
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
            except Exception as e:
                print(f"⚠️ Error parsing event: {e}")

        browser.close()

    print(f"✅ Scraped {len(events)} events from SPL.")
    return events
