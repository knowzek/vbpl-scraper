import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import re
from constants import UNWANTED_TITLE_KEYWORDS

def scrape_vbpl_events(mode="all"):
    base_url = "https://vbpl.librarymarket.com"
    headers = {"User-Agent": "Mozilla/5.0"}
    MAX_PAGES = 50

    events = []
    today = datetime.today()

    if mode in ["weekly", "monthly"]:
        days = 7 if mode == "weekly" else 30
        cutoff_date = today + timedelta(days=days)
    else:
        cutoff_date = None  # No cutoff

    page = 0

    while page < MAX_PAGES:
        print(f"🌐 Fetching page {page}...")
        url = f"{base_url}/events/upcoming?page={page}"
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.select("article.event-card")

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
                description_tag = detail_soup.select_one(".field--name-body .field-item") or \
                                  detail_soup.select_one(".field--name-body")
                
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
