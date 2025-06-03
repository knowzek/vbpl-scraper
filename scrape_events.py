import requests
from bs4 import BeautifulSoup
from datetime import datetime

def scrape_vbpl_events():
    base_url = "https://vbpl.librarymarket.com"
    headers = {"User-Agent": "Mozilla/5.0"}

    events = []
    page = 0

    while True:
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
