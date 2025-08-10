# run_all_scrapers.py

from scrape_npl_events import scrape_npl_events
from scrape_chpl_events import scrape_chpl_events
from scrape_hpl_events import scrape_hpl_events
from scrape_nnpl_events import scrape_nnpl_events
from scrape_spl_events import scrape_spl_events
from scrape_ppl_events import scrape_ppl_events
from scrape_events import scrape_vbpl_events
from scrap_visithampton_events import scrap_visithampton
from upload_to_sheets import upload_events_to_sheet
from constants import LIBRARY_CONSTANTS

from datetime import datetime, timedelta

LIBRARIES = ["vbpl", "npl", "chpl", "nnpl", "hpl", "spl", "ppl", "visithampton"]
MODE = "monthly"  # or "weekly", or "all"

def get_cutoff(mode):
    today = datetime.today()
    if mode == "weekly":
        return today + timedelta(days=7)
    elif mode == "monthly":
        if today.month == 12:
            next_month = datetime(today.year + 1, 1, 1)
        else:
            next_month = datetime(today.year, today.month + 1, 1)
        if next_month.month == 12:
            following_month = datetime(next_month.year + 1, 1, 1)
        else:
            following_month = datetime(next_month.year, next_month.month + 1, 1)
        return following_month - timedelta(days=1)
    return None

def run_all_scrapers():
    for library in LIBRARIES:
        print(f"\n🚀 Scraping {library.upper()}...")
        try:
            if library == "vbpl":
                events = scrape_vbpl_events(mode=MODE)
            elif library == "npl":
                events = scrape_npl_events(mode=MODE)
            elif library == "chpl":
                events = scrape_chpl_events(mode=MODE)
            elif library == "nnpl":
                events = scrape_nnpl_events(mode=MODE)
            elif library == "hpl":
                events = scrape_hpl_events(mode=MODE)
            elif library == "spl":
                events = scrape_spl_events(mode=MODE)
            elif library == "ppl":
                events = scrape_ppl_events(mode=MODE)
            elif library == "visithampton":
                events = scrap_visithampton(mode=MODE)
            else:
                print(f"⚠️ Unknown library: {library}")
                continue

            print(f"✅ {len(events)} events scraped from {library.upper()}")

            if events:
                constants = LIBRARY_CONSTANTS.get(library, {})
                upload_events_to_sheet(
                    events,
                    mode=MODE,
                    library=library,
                    age_to_categories=constants.get("age_to_categories"),
                    name_suffix_map=constants.get("name_suffix_map")
                )
                print(f"📤 Uploaded {library.upper()} events to sheet.")
            else:
                print(f"⚠️ No events to upload for {library.upper()}")

        except Exception as e:
            print(f"❌ Failed to scrape/upload for {library.upper()}: {e}")

if __name__ == "__main__":
    run_all_scrapers()
