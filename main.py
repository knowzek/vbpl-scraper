import sys
from datetime import datetime, timedelta
from scrape_events import scrape_vbpl_events, filter_events_by_mode
from scrape_npl_events import scrape_npl_events
from upload_to_sheets import upload_events_to_sheet
from export_to_csv import export_events_to_csv

# Mapping of age group labels from NPL to their categories
NPL_AGE_TO_CATEGORIES = {
    "Family": "Audience - Free Event, Event Location – Norfolk, Audience - Family Event",
    "All Ages": "Audience - Free Event, Event Location – Norfolk",
    "Babies (0-2)": "Audience - Free Event, Event Location – Norfolk, Audience - Parent & Me, Audience - Toddler/Infant",
    "Toddlers (2-3)": "Audience - Free Event, Event Location – Norfolk, Audience - Parent & Me, Audience - Toddler/Infant",
    "Preschool (3-5)": "Audience - Free Event, Event Location – Norfolk, Audience - Parent & Me, Audience - Preschool Age",
    "Elementary School Age (5-9)": "Audience - Free Event, Event Location – Norfolk, Audience - School Age",
    "Tweens (9-13)": "Audience - Teens, Event Location – Norfolk, Audience - School Age",
    "Teens (12-17)": "Audience - Teens, Event Location – Norfolk, Audience - School Age"
}

if __name__ == "__main__":
    # usage: python main.py [library] [mode]
    library = sys.argv[1] if len(sys.argv) > 1 else "vbpl"
    mode = sys.argv[2] if len(sys.argv) > 2 else "all"

    print(f"🚀 Scraping events for '{library}' (mode: {mode})...")

    cutoff = None
    if mode == "weekly":
        cutoff = datetime.today() + timedelta(days=7)
    elif mode == "monthly":
        today = datetime.today()
        if today.month == 12:
            next_month = datetime(today.year + 1, 1, 1)
        else:
            next_month = datetime(today.year, today.month + 1, 1)
        if next_month.month == 12:
            following_month = datetime(next_month.year + 1, 1, 1)
        else:
            following_month = datetime(next_month.year, next_month.month + 1, 1)
        cutoff = following_month - timedelta(days=1)

    if library == "vbpl":
        events = scrape_vbpl_events(cutoff_date=cutoff)
    elif library == "npl":
        events = scrape_npl_events(mode=mode)
    else:
        raise ValueError(f"Unknown library: {library}")

    print(f"✅ Scraped {len(events)} events total.")

    if mode in ["weekly", "monthly"] and library == "vbpl":
        events = filter_events_by_mode(events, mode)
        print(f"📅 {len(events)} events after {mode} filter.")

    if events:
        print("📤 Uploading to Google Sheets...")
        upload_events_to_sheet(events, mode=mode, library=library, age_to_categories=NPL_AGE_TO_CATEGORIES if library == "npl" else None)
        export_events_to_csv(library=library)
        print("✅ Done.")
    else:
        print("⚠️ No events to upload.")
