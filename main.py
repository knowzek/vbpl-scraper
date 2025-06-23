import sys
from datetime import datetime, timedelta
from scrape_events import scrape_vbpl_events, filter_events_by_mode
from upload_to_sheets import upload_events_to_sheet

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    print(f"🚀 Scraping events (mode: {mode})...")

    # ✅ Set cutoff date based on mode
    cutoff = None
    if mode == "weekly":
        cutoff = datetime.today() + timedelta(days=7)
    elif mode == "monthly":
        today = datetime.today()
        # First day of next month
        if today.month == 12:
            next_month = datetime(today.year + 1, 1, 1)
        else:
            next_month = datetime(today.year, today.month + 1, 1)
    
        # First day of the month after next
        if next_month.month == 12:
            following_month = datetime(next_month.year + 1, 1, 1)
        else:
            following_month = datetime(next_month.year, next_month.month + 1, 1)
    
        cutoff = following_month - timedelta(days=1)  # ← last day of next month

    # ✅ Pass cutoff to scraper
    events = scrape_vbpl_events(cutoff_date=cutoff)
    print(f"✅ Scraped {len(events)} events total.")

    # Still filter again for safety (e.g. if some dates are misparsed)
    if mode in ["weekly", "monthly"]:
        events = filter_events_by_mode(events, mode)
        print(f"📅 {len(events)} events after {mode} filter.")

    if events:
        print("📤 Uploading to Google Sheets...")
        upload_events_to_sheet(events, mode=mode)
        print("✅ Done.")
    else:
        print("⚠️ No events to upload.")
