import sys
from datetime import datetime, timedelta
from scrape_events import scrape_vbpl_events
from scrape_npl_events import scrape_npl_events
from upload_to_sheets import upload_events_to_sheet
from export_to_csv import export_events_to_csv
from scrape_chpl_events import scrape_chpl_events
from scrap_visitchesapeake_events import scrap_visitchesapeake
from constants import LIBRARY_CONSTANTS
from scrape_nnpl_events import scrape_nnpl_events
from scrap_visithampton_events import scrap_visithampton
from scrap_visitnewportnews_events import scrap_visitnewportnews
from scrap_portsvaevents_events import scrap_portsvaevents
from scrap_visitsuffolk_events import scrap_visitsuffolk
from scrap_langleylibrary_events import scrap_langleylibrary


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
        events = scrape_vbpl_events()

    elif library == "poquosonpl":
        from scrape_poquosonpl_events import scrape_poquosonpl_events
        events = scrape_poquosonpl_events(cutoff_date=cutoff, mode=mode)
    
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
        from scrap_visitchesapeake_events import scrap_visitchesapeake
        events = scrap_visitchesapeake(mode=mode)
    
    elif library == "visithampton":
        from scrap_visithampton_events import scrap_visithampton
        events = scrap_visithampton(mode=mode)

    elif library == "visitnewportnews":
        from scrap_visitnewportnews_events import scrap_visitnewportnews
        events = scrap_visitnewportnews(mode=mode)

    elif library == "portsvaevents":
        from scrap_portsvaevents_events import scrap_portsvaevents
        events = scrap_portsvaevents(mode=mode)

    elif library == "ypl":
        from scrape_ypl_events import scrape_YPL_events
        events = scrape_YPL_events(mode=mode)
    
    elif library == "visitsuffolk":
        from scrap_visitsuffolk_events import scrap_visitsuffolk
        events = scrap_visitsuffolk(mode=mode)

    elif library == "visitnorfolk":
        from scrap_visitnorfolk_events import scrap_visitnorfolk_events
        events = scrap_visitnorfolk_events(mode=mode)

    elif library == "visityorktown":
        from scrap_visityorktown_events import scrap_visityorktown_events
        events = scrap_visityorktown_events(mode=mode)
    
    elif library == "langleylibrary":
        from scrap_langleylibrary_events import scrap_langleylibrary
        events = scrap_langleylibrary(mode=mode)

    
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
            age_to_categories=constants.get("age_to_categories", {}), 
            name_suffix_map=constants.get("name_suffix_map", {})  
        )
        # export_events_to_csv(library=library)
        print("✅ Done.")
    else:
        print("⚠️ No events to upload.")
