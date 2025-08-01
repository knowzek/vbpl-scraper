import sys
from datetime import datetime, timedelta
from scrape_events import scrape_vbpl_events
from scrape_npl_events import scrape_npl_events
from upload_to_sheets import upload_events_to_sheet
from export_to_csv import export_events_to_csv
from scrape_chpl_events import scrape_chpl_events
from scrape_visitchesapeake_events import scrape_visitchesapeake_events
from constants import LIBRARY_CONSTANTS
from scrape_nnpl_events import scrape_nnpl_events


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
    
    elif library == "chpl":
        from scrape_chpl_events import scrape_chpl_events
        events = scrape_chpl_events(mode=mode)
    
    elif library == "hpl":
        from scrape_hpl_events import scrape_hpl_events
        events = scrape_hpl_events(mode=mode)
    
    elif library == "nnpl":
        import asyncio
        from scrape_nnpl_events import scrape_nnpl_events
        events = scrape_nnpl_events(mode=mode)

    elif library == "spl":
        from scrape_spl_events import scrape_spl_events
        events = scrape_spl_events(mode=mode)
    
    elif library == "ppl":
        from scrape_ppl_events import scrape_ppl_events
        events = scrape_ppl_events(mode=mode)

    elif library == "vbpr":
        from scrape_vbpr_events import scrape_vbpr_events
        events = scrape_vbpr_events(mode=mode)

    elif library == "visitchesapeake":
        from scrape_visitchesapeake_events import scrape_visitchesapeake_events
        events = scrape_visitchesapeake_events(mode=mode)
    
    else:
        raise ValueError(f"Unknown library: {library}")

    print(f"✅ Scraped {len(events)} events total.")

    if mode in ["weekly", "monthly"] and library == "vbpl":
        events = filter_events_by_mode(events, mode)
        print(f"📅 {len(events)} events after {mode} filter.")

    if events:
        print("📤 Uploading to Google Sheets...")
        constants = LIBRARY_CONSTANTS.get(library, {})
        upload_events_to_sheet(
            events,
            mode=mode,
            library=library,
            age_to_categories=constants.get("age_to_categories"),
            name_suffix_map=constants.get("name_suffix_map")
        )
        # export_events_to_csv(library=library)
        print("✅ Done.")
    else:
        print("⚠️ No events to upload.")
