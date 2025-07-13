from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
from playwright.sync_api import sync_playwright
from constants import LIBRARY_CONSTANTS, TITLE_KEYWORD_TO_CATEGORY, UNWANTED_TITLE_KEYWORDS

BASE_URL = "https://suffolkpubliclibrary.libcal.com/calendar"
UNWANTED_PROGRAM_TYPES = {
    "Adult",
    "Adult (Older Adult)",
    "Library2Go",
    "Child Care Providers"
}

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

        page_number = 1
        while True:
            print(f"📄 Fetching page {page_number}...")
            page.goto(f"{BASE_URL}?cid=-1&t=d&d=0000-00-00&cal=-1&page={page_number}&inc=0", timeout=30000)
            try:
                page.wait_for_selector(".s-lc-c-evt", timeout=5000)
            except:
                print("🛑 No more events found or timed out.")
                break
            
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            event_listings = soup.find_all("div", class_="media s-lc-c-evt")

            if not event_listings:
                print("🛑 No more events found.")
                break
        
            for listing in event_listings:
                try:
                    # Extract category (Program Type)
                    category_tag = listing.select_one("span.s-lc-event-category-link a")
                    program_type = category_tag.get_text(strip=True) if category_tag else ""
                    # Extract audience tags from category list
                    audience_tags = [tag.get_text(strip=True) for tag in listing.select("span.s-lc-event-audience-link a")]

                    # Filter out unwanted categories
                    if program_type in UNWANTED_PROGRAM_TYPES:
                        print(f"⏭️ Skipping: Unwanted category → {program_type}")
                        continue
    
                    title_tag = listing.find("h3", class_="media-heading")
                    raw_title = title_tag.get_text(strip=True) if title_tag else "Untitled Event"
                    title = re.sub(r"\s*\[.*?\]", "", raw_title).strip()
                    url_tag = title_tag.find("a") if title_tag else None
                    url = url_tag["href"] if url_tag and url_tag.has_attr("href") else ""
                    
                    desc_tag = listing.find("div", class_="s-lc-c-evt-des")
                    desc = desc_tag.get_text(strip=True) if desc_tag else ""
                    
                    # ✅ Clean up truncated descriptions
                    if desc.endswith("...") or desc.endswith("…"):
                        # Remove the trailing dots
                        desc = desc.rstrip(".… ").strip()
                        
                        # Try to truncate to the last full sentence
                        last_punct = max(desc.rfind("."), desc.rfind("!"), desc.rfind("?"))
                        if last_punct != -1:
                            desc = desc[:last_punct + 1].strip()

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
                    
                    # ✅ Skip "Closed for..." events
                    if any(bad_word in title.lower() for bad_word in UNWANTED_TITLE_KEYWORDS):
                        print(f"⏭️ Skipping: Unwanted title match → {title}")
                        continue
                    
                    if is_likely_adult_event(title) or is_likely_adult_event(desc):
                        continue
    
                    time_str = info.get("time", "")
                    raw_location = info.get("location", "").strip()
                    venue_map = LIBRARY_CONSTANTS["spl"].get("venue_names", {})
                    
                    # Normalize for known venue mappings unless it's a mobile/SPL2GO event
                    if "spl2go" in title.lower():
                        location = raw_location  # Keep full location for mobile events
                    else:
                        location = None
                        for key in venue_map:
                            if key.lower() in raw_location.lower():
                                location = venue_map[key]
                                break
                        if not location:
                            location = raw_location  # Fallback if not matched
                    
                    venue = location  # Final value passed to the sheet

                    if audience_tags:
                        ages = ", ".join(sorted(set(audience_tags)))
                    else:
                        ages = extract_ages(title + " " + desc)

                    # Normalize title formatting for SPL — only add location if it's not already there
                    if location.lower() not in title.lower():
                        full_title = f"{title} at {location}"
                    else:
                        full_title = title
                    
                    event_name = f"{full_title} ({location})"
                    
                    # Build categories from both Program Type and Keywords
                    title_lower = title.lower()
                    keyword_tags = [tag for keyword, tag in TITLE_KEYWORD_TO_CATEGORY.items() if keyword in title_lower]
                    keyword_category_str = ", ".join(keyword_tags)
                    
                    program_type_categories = ""
                    if program_type:
                        program_type_categories = LIBRARY_CONSTANTS["spl"].get("program_type_to_categories", {}).get(program_type, "")
                    
                    all_categories = ", ".join(filter(None, [program_type_categories, keyword_category_str]))
                    
                    events.append({
                        "Event Name": f"{full_title} ({location})",
                        "Event Link": url,
                        "Event Status": "Available",
                        "Time": time_str,
                        "Ages": ages,
                        "Location": venue,
                        "Month": dt.strftime("%b"),
                        "Day": str(dt.day),
                        "Year": str(dt.year),
                        "Event Date": dt.strftime("%Y-%m-%d"),
                        "Event End Date": dt.strftime("%Y-%m-%d"),
                        "Event Description": desc,
                        "Series": "",
                        "Program Type": program_type,
                        "Categories": all_categories
                    })
                except Exception as e:
                    print(f"⚠️ Error parsing event: {e}")
            page_number += 1
        browser.close()

    print(f"✅ Scraped {len(events)} events from SPL.")
    return events
