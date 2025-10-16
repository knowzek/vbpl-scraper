# run_all_scrapers.py

from datetime import datetime, timedelta

# ── Scraper imports (kept exactly as in your current file) ───────────
from scrape_npl_events import scrape_npl_events
from scrape_chpl_events import scrape_chpl_events
from scrape_hpl_events import scrape_hpl_events
from scrape_nnpl_events import scrape_nnpl_events
from scrape_spl_events import scrape_spl_events
from scrape_ppl_events import scrape_ppl_events
from scrape_events import scrape_vbpl_events
from scrape_ypl_events import scrape_ypl_events
from scrape_vbpr_events import scrape_vbpr_events
from scrape_visithampton_hmva_ical import scrape_visithampton_hmva_ical
from scrap_visitchesapeake_events import scrap_visitchesapeake
from scrap_visitnewportnews_events import scrap_visitnewportnews
from scrap_portsvaevents_events import scrap_portsvaevents
from scrap_visitsuffolk_events import scrap_visitsuffolk
from scrap_visitnorfolk_events import scrap_visitnorfolk_events
from scrap_visityorktown_events import scrap_visityorktown_events
from scrape_poquosonpl_events import scrape_poquosonpl_events
from scrap_langleylibrary_events import scrap_langleylibrary

from upload_to_sheets import upload_events_to_sheet
from constants import LIBRARY_CONSTANTS

# ── Libraries registry (unchanged) ───────────────────────────────────
LIBRARIES = [
    "vbpl",
    "npl",
    "chpl",
    "nnpl",
    "hpl",
    "spl",
    "ppl",
    "ypl",
    "vbpr",
    "visithampton",
    "visitchesapeake",
    "visitnewportnews",
    "portsvaevents",
    "visitsuffolk",
    "visitnorfolk",
    "visityorktown",
    "poquosonpl",
    "langleylibrary",
]

# Scraper call mode: keep wide so post-filter enforces exact 4w/12w
SCRAPER_CALL_MODE = "all"   # ("all" is safest; use "monthly"/"weekly" if a site needs it)

WINDOW_MAP = {
    "4w": 28,   # days from today (inclusive)
    "12w": 84,
}

# Map library key -> callable so we can simplify the loop
CALL_MAP = {
    "vbpl": scrape_vbpl_events,
    "npl": scrape_npl_events,
    "chpl": scrape_chpl_events,
    "nnpl": scrape_nnpl_events,
    "hpl": scrape_hpl_events,
    "spl": scrape_spl_events,
    "ppl": scrape_ppl_events,
    "ypl": scrape_YPL_events,
    "vbpr": scrape_vbpr_events,
    "visithampton": scrape_visithampton_hmva_ical,
    "visitchesapeake": scrap_visitchesapeake,
    "visitnewportnews": scrap_visitnewportnews,
    "portsvaevents": scrap_portsvaevents,
    "visitsuffolk": scrap_visitsuffolk,
    "visitnorfolk": scrap_visitnorfolk_events,
    "visityorktown": scrap_visityorktown_events,
    "poquosonpl": scrape_poquosonpl_events,
    "langleylibrary": scrap_langleylibrary,
}

def _parse_date(ev):
    """
    Try several common keys your scrapers return and normalize to date().
    Defaults to None if unparseable (so we keep it for QA/Needs Attention).
    """
    for key in ("Event Date", "Date", "Start Date"):
        val = ev.get(key)
        if not val:
            continue
        s = str(val).strip()
        # common formats: YYYY-MM-DD, MM/DD/YYYY, YYYY-MM-DDTHH:MM:SS
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(s, fmt).date()
            except Exception:
                pass
    return None

def _within_window(ev, last_day):
    d = _parse_date(ev)
    # keep undated events so you can see/fix them; otherwise filter by cutoff
    return True if d is None else (d <= last_day)

def run_all_scrapers(window: str = "12w"):
    window = (window or "").lower().strip()
    if window not in WINDOW_MAP:
        raise SystemExit("Usage: run_all_scrapers.py [4w|12w]")

    today = datetime.today().date()
    last_day = today + timedelta(days=WINDOW_MAP[window])
    print(f"🗓️  Mode: {window} → collecting events through {last_day}")

    for library in LIBRARIES:
        print(f"\n🚀 Scraping {library.upper()}...")
        try:
            fn = CALL_MAP.get(library)
            if not fn:
                print(f"⚠️ No scraper wired for {library}")
                continue

            # Call each scraper with a wide mode; override per-site here if needed
            events = fn(mode=SCRAPER_CALL_MODE)
            print(f"✅ {len(events)} events scraped from {library.upper()}")

            # Central date-window filter
            filtered = [e for e in events if _within_window(e, last_day)]
            print(f"🧮 {len(filtered)}/{len(events)} within {WINDOW_MAP[window]} days for {library.upper()}")

            if filtered:
                constants = LIBRARY_CONSTANTS.get(library, {})
                upload_events_to_sheet(
                    filtered,
                    mode=window,               # log 4w / 12w in your Master Events Log
                    library=library,
                    age_to_categories=constants.get("age_to_categories"),
                    name_suffix_map=constants.get("name_suffix_map"),
                )
                print(f"📤 Uploaded {library.upper()} events to sheet.")
            else:
                print(f"⚠️ No events to upload for {library.upper()} after window filter.")

        except Exception as e:
            print(f"❌ Failed to scrape/upload for {library.upper()}: {e}")

if __name__ == "__main__":
    import sys
    run_all_scrapers(sys.argv[1] if len(sys.argv) > 1 else "12w")
