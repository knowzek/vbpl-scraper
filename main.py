import sys
import asyncio
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
from scrape_poquosonpl_events import scrape_poquosonpl_events
from scrape_hpl_events import scrape_hpl_events
from scrape_spl_events import scrape_spl_events
from scrape_ppl_events import scrape_ppl_events
from scrape_vbpr_events import scrape_vbpr_events
from scrape_ypl_events import scrape_YPL_events
from scrap_visitnorfolk_events import scrap_visitnorfolk_events
from scrap_visityorktown_events import scrap_visityorktown_events
from datetime import datetime, timedelta
import re

def _parse_event_date(ev):
    m = (ev.get("Month") or "").strip()
    d = (ev.get("Day") or "").strip()
    y = (ev.get("Year") or "").strip()
    for fmt in ("%B %d %Y", "%b %d %Y"):
        try:
            return datetime.strptime(f"{m} {d} {y}", fmt)
        except Exception:
            pass
    return None

def filter_events_by_mode(events, mode, now=None):
    """Graceful fallback if some scrapers don’t filter by themselves."""
    if not events: 
        return events
    if now is None:
        now = datetime.now()
    today = now.date()
    if mode == "weekly":
        horizon = today + timedelta(days=7)
        return [ev for ev in events if (dt := _parse_event_date(ev)) is None or today <= dt.date() <= horizon]
    if mode == "monthly":
        return [ev for ev in events if (dt := _parse_event_date(ev)) is None or (dt.year == today.year and dt.month == today.month)]
    return events  # "full"

def _call_scraper(fn, **kwargs):
    """Call a scraper; if it rejects kwargs (e.g., cutoff_date), retry without them."""
    try:
        return fn(**kwargs)
    except TypeError as e:
        if "unexpected keyword argument" in str(e):
            return fn()  # legacy signature
        raise



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
        events = _call_scraper(scrape_vbpl_events, mode=mode, cutoff_date=cutoff)
    
    elif library == "poquosonpl":
        events = _call_scraper(scratch := scrape_poquosonpl_events, mode=mode, cutoff_date=cutoff)
    
    elif library == "npl":
        events = _call_scraper(scrape_npl_events, mode=mode, cutoff_date=cutoff)
    
    elif library == "chpl":
        events = _call_scraper(scrape_chpl_events, mode=mode, cutoff_date=cutoff)
    
    elif library == "hpl":
        events = _call_scraper(scrape_hpl_events, mode=mode, cutoff_date=cutoff)
    
    elif library == "nnpl":
        events = _call_scraper(scrape_nnpl_events, mode=mode, cutoff_date=cutoff)
    
    elif library == "spl":
        events = _call_scraper(scrape_spl_events, mode=mode, cutoff_date=cutoff)
    
    elif library == "ppl":
        events = _call_scraper(scrape_ppl_events, mode=mode, cutoff_date=cutoff)
    
    elif library == "vbpr":
        events = _call_scraper(scrape_vbpr_events, mode=mode, cutoff_date=cutoff)
    
    elif library == "visitchesapeake":
        events = _call_scraper(scap := scrap_visitchesapeake, mode=mode, cutoff_date=cutoff)
    
    elif library == "visithampton":
        events = _call_scraper(scap := scrap_visithampton, mode=mode, cutoff_date=cutoff)
    
    elif library == "visitnewportnews":
        events = _call_scraper(scap := scrap_visitnewportnews, mode=mode, cutoff_date=cutoff)
    
    elif library == "portsvaevents":
        events = _call_scraper(scap := scrap_portsvaevents, mode=mode, cutoff_date=cutoff)
    
    elif library == "ypl":
        events = _call_scraper(scrape_YPL_events, mode=mode, cutoff_date=cutoff)
    
    elif library == "visitsuffolk":
        events = _call_scraper(scap := scrap_visitsuffolk, mode=mode, cutoff_date=cutoff)
    
    elif library == "visitnorfolk":
        events = _call_scraper(scap := scrap_visitnorfolk_events, mode=mode, cutoff_date=cutoff)
    
    elif library == "visityorktown":
        events = _call_scraper(scap := scrap_visityorktown_events, mode=mode, cutoff_date=cutoff)
    
    elif library == "langleylibrary":
        events = _call_scraper(scap := scrap_langleylibrary, mode=mode, cutoff_date=cutoff)
    
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
