
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
from constants import TITLE_KEYWORD_TO_CATEGORY

def is_likely_adult_event(text):
    text = text.lower()
    return any(kw in text for kw in ["adults", "adult", "18+", "21+"])

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
    print("🎯 Scraping VBPR events via Playwright...")

    today = datetime.today()
    if mode == "weekly":
        end_cutoff = today + timedelta(days=7)
    elif mode == "monthly":
        end_cutoff = today + timedelta(days=31)
    else:
        end_cutoff = today + timedelta(days=90)

    events = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://anc.apm.activecommunities.com/vbparksrec/activity/search?activity_select_param=2&viewMode=list", timeout=60000)

        # Explicitly click the "Search" button to trigger results
        search_button = page.query_selector("button.btn.btn-primary[type='submit']")
        if search_button:
            search_button.click()
            page.wait_for_timeout(3000)
        
        while True:
            page.wait_for_timeout(5000)  # Just wait, no selector
        
            if page.query_selector(".searchNoResults"):
                print("⚠️ No results loaded. Exiting.")
                break

            soup = BeautifulSoup(page.content(), "html.parser")
            cards = soup.select(".activityItem")

            if not cards:
                break

            for card in cards:
                try:
                    title_tag = card.select_one(".activityTitle")
                    name = title_tag.get_text(strip=True) if title_tag else "Untitled Event"

                    if is_likely_adult_event(name):
                        continue

                    detail_link_tag = card.select_one("a.activityTitleLink")
                    link = "https://anc.apm.activecommunities.com" + detail_link_tag["href"] if detail_link_tag else ""

                    date_range = card.select_one(".activityDates")
                    date_text = date_range.get_text(strip=True) if date_range else ""
                    start_date = None
                    end_date_str = ""

                    if " to " in date_text:
                        try:
                            parts = date_text.split(" to ")
                            start_date = datetime.strptime(parts[0], "%B %d, %Y")
                            end_date_str = datetime.strptime(parts[1], "%B %d, %Y").strftime("%Y-%m-%d")
                        except Exception:
                            continue
                    else:
                        try:
                            start_date = datetime.strptime(date_text, "%B %d, %Y")
                            end_date_str = start_date.strftime("%Y-%m-%d")
                        except Exception:
                            continue

                    if start_date > end_cutoff:
                        continue
    
                    time_tag = card.select_one(".activityTimes")
                    time = time_tag.get_text(strip=True) if time_tag else ""

                    site_tag = card.select_one(".activityLocation")
                    site = site_tag.get_text(strip=True) if site_tag else ""

                    desc_tag = card.select_one(".activityDesc")
                    desc = desc_tag.get_text(strip=True) if desc_tag else ""

                    category_tag = card.select_one(".activityCategory")
                    category = category_tag.get_text(strip=True) if category_tag else ""

                    ages = extract_ages(name + " " + desc)

                    month = start_date.strftime("%b")
                    day = str(start_date.day)
                    year = str(start_date.year)

                    title_lower = name.lower()
                    keyword_tags = [tag for keyword, tag in TITLE_KEYWORD_TO_CATEGORY.items() if keyword in title_lower]
                    keyword_category_str = ", ".join(keyword_tags)

                    program_type_categories = ""
                    if category == "Fitness & Wellness":
                        program_type_categories = "Event Location - Virginia Beach, List - Fitness Events"

                    categories = ", ".join(filter(None, [program_type_categories, keyword_category_str]))

                    events.append({
                        "Event Name": f"{name} (Virginia Beach)",
                        "Event Link": link,
                        "Event Status": "Available",
                        "Time": time,
                        "Ages": ages,
                        "Location": site,
                        "Month": month,
                        "Day": day,
                        "Year": year,
                        "Event Date": start_date.strftime("%Y-%m-%d"),
                        "Event End Date": end_date_str,
                        "Event Description": desc,
                        "Series": "",
                        "Program Type": category,
                        "Categories": categories
                    })
                except Exception as e:
                    print(f"⚠️ Error parsing card: {e}")

            next_button = page.query_selector("li.next:not(.disabled) a")
            if next_button:
                next_button.click()
                page.wait_for_timeout(2000)
            else:
                break

        browser.close()

    print(f"✅ Scraped {len(events)} VBPR events.")
    return events
