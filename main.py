from scrape_events import scrape_vbpl_events
from upload_to_sheets import upload_events_to_sheet

if __name__ == "__main__":
    print("🚀 Scraping events...")
    events = scrape_vbpl_events()
    print(f"✅ Scraped {len(events)} events.")

    if events:
        print("📤 Uploading to Google Sheets...")
        upload_events_to_sheet(events)
        print("✅ Done.")
    else:
        print("⚠️ No events found.")
