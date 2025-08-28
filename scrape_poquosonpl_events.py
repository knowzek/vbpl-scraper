import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import re
from constants import UNWANTED_TITLE_KEYWORDS

base_url = "https://poquoson.librarycalendar.com"
headers = {"User-Agent": "Mozilla/5.0"}
MAX_PAGES = 50

import re

def extract_description(soup):
    """
    Robustly extract description from LibraryCalendar (LibraryMarket) pages.
    Handles both `.field--name-description` and `.field--name-body`,
    preserves basic line breaks and bullet lists.
    """
    # Try the usual suspects, in order
    sel = (
        ".field--name-description .field-item, "
        ".field--name-description, "
        ".field--name-body .field-item, "
        ".field--name-body, "
        ".event-body"
    )
    node = soup.select_one(sel)

    # Last-resort: meta description
    if not node:
        meta = soup.select_one('meta[name="description"]')
        return (meta["content"].strip() if meta and meta.get("content") else "")

    # Normalize HTML → text
    # 1) <br> → newline
    for br in node.find_all("br"):
        br.replace_with("\n")
    # 2) bullet lists → "- item" lines
    for li in node.find_all("li"):
        li.insert_before("\n- ")
    # Ensure paragraphs create spacing
    for p in node.find_all("p"):
        if p.text and not p.text.endswith("\n"):
            p.append("\n\n")

    text = node.get_text(separator="\n", strip=True)

    # Collapse excessive newlines
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def scrape_poquosonpl_events(cutoff_date=None, mode="all"):
    
    events = []
    today = datetime.today()

    # allow main.py to pass cutoff_date; otherwise compute from mode
    if cutoff_date is None:
        if mode == "weekly":
            cutoff_date = today + timedelta(days=7)
        elif mode == "monthly":
            cutoff_date = today + timedelta(days=30)
        else:
            cutoff_date = today + timedelta(days=90)

    page = 0

    while page < MAX_PAGES:
        print(f"🌐 Fetching page {page}...")
        url = f"{base_url}/events/upcoming?page={page}"
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.select("article.lc-event-card, article.event-card, article.node--type-event")
        if not cards:
            print("✅ No more event cards found. Done scraping.")
            break

        for card in cards:
            try:
                link_tag = card.select_one("a.lc-event__link")
                name = link_tag.get_text(strip=True)
                link = base_url + link_tag["href"]
                # 🚫 Skip unwanted titles
                if any(bad_word in name.lower() for bad_word in UNWANTED_TITLE_KEYWORDS):
                    print(f"⏭️ Skipping: Unwanted title match → {name}")
                    continue
                print(f"🔗 Processing: {name} ({link})")

                # Extract event date from the card
                month_tag = card.select_one(".lc-date-icon__item--month")
                day_tag = card.select_one(".lc-date-icon__item--day")
                year_tag = card.select_one(".lc-date-icon__item--year")

                month_text = month_tag.get_text(strip=True) if month_tag else ""
                day_text = day_tag.get_text(strip=True) if day_tag else ""
                year_text = year_tag.get_text(strip=True) if year_tag else ""

                if not (month_text and day_text and year_text):
                    print(f"⚠️ Missing date parts for '{name}' — skipping")
                    continue

                try:
                    event_date = datetime.strptime(f"{month_text} {day_text} {year_text}", "%b %d %Y")
                except Exception as e:
                    print(f"⚠️ Failed to parse date for '{name}': {e}")
                    continue

                print(f"📅 Parsed date for '{name}': {event_date.date()}")

                if cutoff_date and event_date > cutoff_date:
                    print(f"🛑 '{name}' is beyond cutoff ({cutoff_date.date()}). Stopping pagination.")
                    return events

                # Extract summary info from card
                time_tag = card.select_one(".lc-event-info-item--time")
                time_slot = time_tag.get_text(strip=True) if time_tag else ""

                ages_tag = card.select_one(".lc-event-info__item--colors")
                ages = ages_tag.get_text(strip=True) if ages_tag else ""

                status_tag = card.select_one(".lc-registration-label")
                status = status_tag.get_text(strip=True) if status_tag else "Available"

                location_tag = card.select_one(".lc-event__branch")
                location = location_tag.get_text(strip=True) if location_tag else ""

                # Fetch detail page
                time.sleep(0.5)
                detail_response = requests.get(link, headers=headers, timeout=20)
                detail_soup = BeautifulSoup(detail_response.text, "html.parser")

                # Extract description
                # detail page
                time.sleep(0.4)
                d_resp = requests.get(link, headers=HEADERS, timeout=20)
                d_resp.raise_for_status()
                d_soup = BeautifulSoup(d_resp.text, "html.parser")
                
                # ✅ robust description extraction
                description = extract_description(d_soup)

                if description_tag:
                    # Convert HTML line breaks to actual line breaks
                    for br in description_tag.find_all("br"):
                        br.replace_with("\n")
                
                    # Extract text with paragraph spacing
                    description = description_tag.get_text(separator="\n\n", strip=True)
                
                    # Clean excess spacing
                    description = re.sub(r'\n{3,}', '\n\n', description)
                else:
                    description = ""


                # Extract Program Type (used for category assignment)
                program_type_tag = detail_soup.select_one(".lc-event__program-types span")
                program_type = program_type_tag.get_text(strip=True) if program_type_tag else ""

                
                # Detect if part of a series
                series_block = detail_soup.select_one(".lc-repeating-dates__details")
                is_series = "Yes" if series_block else ""

                # Append event to list
                events.append({
                    "Event Name": name,
                    "Event Link": link,
                    "Event Status": status,
                    "Time": time_slot,
                    "Ages": ages,
                    "Location": location,
                    "Month": month_text,
                    "Day": day_text,
                    "Year": year_text,
                    "Event Date": event_date.strftime("%Y-%m-%d"),
                    "Event Description": description,
                    "Series": is_series,
                    "Program Type": program_type
                })

            except Exception as e:
                print(f"⚠️ Error parsing event: {e}")

        page += 1

    print(f"✅ Scraped {len(events)} total events.")
    return events
