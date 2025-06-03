import sys
from scrape_events import scrape_vbpl_events, filter_events_by_mode
from upload_to_sheets import upload_events_to_sheet

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    print(f"🚀 Scraping events (mode: {mode})...")
    events = scrape_vbpl_events()
    print(f"✅ Scraped {len(events)} events total.")

    if mode in ["weekly", "monthly"]:
        events = filter_events_by_mode(events, mode)
        print(f"📅 {len(events)} events after {mode} filter.")

    if events:
        print("📤 Uploading to Google Sheets...")
        upload_events_to_sheet(events, mode=mode)
        print("✅ Done.")
    else:
        print("⚠️ No events to upload.")
