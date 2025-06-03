import requests
from bs4 import BeautifulSoup
import re

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
                # [your existing card parsing logic here...]
                ...
                events.append({
                    # your event fields
                })
            except Exception as e:
                print(f"⚠️ Error parsing event: {e}")
        
        page += 1

    return events
