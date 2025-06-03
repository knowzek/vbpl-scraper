import requests
from bs4 import BeautifulSoup
from datetime import datetime

def scrape_vbpl_events():
    base_url = "https://vbpl.librarymarket.com"
    headers = {"User-Agent": "Mozilla/5.0"}
    MAX_PAGES = 100  # Safety cap to avoid infinite loops

    events = []
    page = 1

    while page < MAX_PAGES:
        print(f"🌐 Fetching page {page}...")
        url = f"{base_url}/events/upcoming?page={page}"
        response = requests.get(url, headers=headers, timeout=10)
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

                time_tag = card.select_one(".lc-event-info-item--time")
                time_slot = time_tag.get_text(strip=True) if time_tag else ""

                ages_tag = card.select_one(".lc-event-info__item--colors")
                ages = ages_tag.get_text(strip=True) if ages_tag else ""

                status_tag = card.select_one(".lc-registration-label")
                status = status_tag.get_text(strip=True) if status_tag else "Available"

                location_tag = card.select_one(".lc-event__branch")
                location = location_tag.get_text(strip=True) if location_tag else ""

                # Visit detail page
                detail_response = requests.get(link, headers=headers, timeout=10)
                detail_soup = BeautifulSoup(detail_response.text, "html.parser")

                description_tag = detail_soup.select_one(".field--name-body .field-item") or \
                                  detail_soup.select_one(".field--name-body")
                description = description_tag.get_text(strip=True) if description_tag else ""

                month = detail_soup.select_one(".lc-date-icon__item--month")
                day = detail_soup.select_one(".lc-date-icon__item--day")
                year = detail_soup.select_one(".lc-date-icon__item--year")

                month_text = month.get_text(strip=True) if month else ""
                day_text = day.get_text(strip=True) if day else ""
                year_text = year.get_text(strip=True) if year else ""

                try:
                    event_date = datetime.strptime(f"{month_text} {day_text} {year_text}", "%B %d %Y")
                except Exception as e:
                    event_date = None

                # Optional: Stop if too far in the future (2+ months out)
                if event_date and event_date > datetime.today().replace(day=1).replace(month=datetime.today().month + 2):
                    print("🛑 Hit future month cutoff, stopping pagination.")
                    return events

                if not link or not name:
                    print(f"⚠️ Missing critical data, skipping event: name={name}, link={link}")
                    continue

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
                    "Event Description": description
                })

            except Exception as e:
                print(f"⚠️ Error parsing event: {e}")

        page += 1

    print(f"✅ Scraped {len(events)} total events.")
    return events
