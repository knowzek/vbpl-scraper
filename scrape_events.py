import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
from datetime import timedelta

def filter_events_by_mode(events, mode):
    today = datetime.today()

    if mode == "weekly":
        end_date = today + timedelta(days=7)
    elif mode == "monthly":
        end_date = datetime(today.year, today.month, 28) + timedelta(days=4)
        end_date = end_date.replace(day=1) - timedelta(days=1)
    else:
        return events  # no filtering

    filtered = []
    for event in events:
        try:
            edate = datetime.strptime(event["Event Date"], "%Y-%m-%d")
            if today <= edate <= end_date:
                filtered.append(event)
        except:
            continue
    return filtered

def scrape_vbpl_events(cutoff_date=None):
    base_url = "https://vbpl.librarymarket.com"
    headers = {"User-Agent": "Mozilla/5.0"}
    MAX_PAGES = 100

    events = []
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
                print(f"🔗 Processing: {name} ({link})")

                # ✅ Extract event date from the card (not detail page)
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

                # Fetch detail page
                time.sleep(0.5)
                detail_response = requests.get(link, headers=headers, timeout=10)
                detail_soup = BeautifulSoup(detail_response.text, "html.parser")
                
                # Extract description
                description_tag = detail_soup.select_one(".field--name-body .field-item") or \
                                  detail_soup.select_one(".field--name-body")
                description = description_tag.get_text(strip=True) if description_tag else ""
                
                # ✅ Detect if this event is part of a series
                series_block = detail_soup.select_one(".lc-repeating-dates__details")
                is_series = "Yes" if series_block else ""
                
                # Append full event
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
                    "Event Date": event_date.strftime("%Y-%m-%d") if event_date else "",
                    "Event Description": description,
                    "Series": is_series
                })
            except Exception as e:
                print(f"⚠️ Error parsing event: {e}")

        page += 1

    print(f"✅ Scraped {len(events)} total events.")
    return events
