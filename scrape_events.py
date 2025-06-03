import requests
from bs4 import BeautifulSoup
import re

def remove_emojis(text):
    return re.sub(r"[^\w\s.,;:!?&@()'\"/-]", "", text)

def scrape_vbpl_events():
    base_url = "https://vbpl.librarymarket.com"
    month_url = f"{base_url}/events/upcoming"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(month_url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    cards = soup.select("article.event-card")
    events = []

    for card in cards:
        try:
            link_tag = card.select_one("a.lc-event__link")
            name = remove_emojis(link_tag.get_text(strip=True))
            link = base_url + link_tag["href"]

            time_tag = card.select_one(".lc-event-info-item--time")
            time_slot = remove_emojis(time_tag.get_text(strip=True)) if time_tag else ""

            ages_tag = card.select_one(".lc-event-info__item--colors")
            ages = remove_emojis(ages_tag.get_text(strip=True)) if ages_tag else ""

            status_tag = card.select_one(".lc-registration-label")
            status = remove_emojis(status_tag.get_text(strip=True)) if status_tag else "Available"

            location_tag = card.select_one(".lc-event__branch")
            location = remove_emojis(location_tag.get_text(strip=True)) if location_tag else ""

            # Visit detail page
            detail_response = requests.get(link, headers=headers)
            detail_soup = BeautifulSoup(detail_response.text, "html.parser")

            description_tag = detail_soup.select_one(".field--name-body .field-item")
            description = remove_emojis(description_tag.get_text(strip=True)) if description_tag else ""

            month = detail_soup.select_one(".lc-date-icon__item--month")
            day = detail_soup.select_one(".lc-date-icon__item--day")
            year = detail_soup.select_one(".lc-date-icon__item--year")

            events.append({
                "Event Name": name,
                "Event Link": link,
                "Event Status": status,
                "Time": time_slot,
                "Ages": ages,
                "Location": location,
                "Month": month.get_text(strip=True) if month else "",
                "Day": day.get_text(strip=True) if day else "",
                "Year": year.get_text(strip=True) if year else "",
                "Event Description": description
            })

        except Exception as e:
            print(f"⚠️ Error parsing event: {e}")

    return events
