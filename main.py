import sys
from datetime import datetime, timedelta
from scrape_events import scrape_vbpl_events, filter_events_by_mode
from scrape_npl_events import scrape_npl_events
from upload_to_sheets import upload_events_to_sheet
from export_to_csv import export_events_to_csv
from scrape_chpl_events import scrape_chpl_events

# Mapping of age group labels from NPL to their categories
NPL_AGE_TO_CATEGORIES = {
    "Family": "Audience - Free Event, Event Location - Norfolk, Audience - Family Event",
    "All Ages": "Audience - Free Event, Event Location - Norfolk",
    "Babies (0-2)": "Audience - Free Event, Event Location - Norfolk, Audience - Parent & Me, Audience - Toddler/Infant",
    "Toddlers (2-3)": "Audience - Free Event, Event Location - Norfolk, Audience - Parent & Me, Audience - Toddler/Infant",
    "Preschool (3-5)": "Audience - Free Event, Event Location - Norfolk, Audience - Parent & Me, Audience - Preschool Age",
    "Elementary School Age (5-9)": "Audience - Free Event, Event Location - Norfolk, Audience - School Age",
    "Tweens (9-13)": "Audience - Teens, Event Location - Norfolk, Audience - School Age",
    "Teens (12-17)": "Audience - Teens, Event Location - Norfolk, Audience - School Age"
}

# Mapping of NPL campus names to simplified suffixes for event titles
NPL_LIBRARY_NAME_SUFFIXES = {
    "Mary D. Pretlow Anchor Branch Library": "Pretlow Library",
    "Barron F. Black Branch Library": "Barron F. Black Library",
    "Richard A. Tucker Memorial Library": "Tucker Library",
    "Larchmont Branch Library": "Larchmont Library",
    "Jordan-Newby Anchor Branch Library at Broad Creek": "Jordan-Newby Anchor Branch Library",
    "Blyden Branch Library": "Blyden Branch Library",
    "Lafayette Branch Library": "Lafayette Branch Library",
    "Van Wyck Branch Library": "Van Wyck Branch Library",
    "Downtown Branch at Slover": "Downtown Branch at Slover",
    "Park Place Branch Library": "Park Place Branch Library",
    "Little Creek Branch Library": "Little Creek Branch Library",
    "Janaf Branch Library": "Janaf Branch Library"
}

# Mapping of age group labels from NPL to their categories
CHPL_AGE_TO_CATEGORIES = {
    "Preschool": "Audience - Preschool Age, Audience - Free Event, Event Location - Chesapeake, Audience - Parent & Me, Audience - Toddler/Infant",
    "Elementary School": "Audience - School Age, Audience - Free Event, Event Location - Chesapeake",
    "Middle School": "Audience - Teens, Audience - Free Event, Event Location - Chesapeake",
    "High School": "Audience - Teens, Audience - Free Event, Event Location - Chesapeake",
    "Families": "Audience - Family Event, Audience - Free Event, Event Location - Chesapeake",
    "All Ages": "Audience - All Ages, Audience - Free Event, Event Location - Chesapeake",
    "Adult": "Audience - Adult Event, Audience - Free Event, Event Location - Chesapeake"
}

CHPL_NAME_SUFFIXES = {
    "Dr. Clarence V. Cuffee Outreach and Innovation Library": "Cuffee Library",
    "Greenbrier Library": "Greenbrier Library",
    "Russell Memorial Library": "Russell Library",
    "Major Hillard Library": "Major Hillard Library"
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
    
    elif library == "chpl":
        from scrape_chpl_events import scrape_chpl_events
        events = scrape_chpl_events(mode=mode)
    
    elif library == "hpl":
        from scrape_hpl_events import scrape_hpl_events
        events = scrape_hpl_events(mode=mode)
    
    elif library == "nnpl":
        from scrape_nnpl_events import scrape_nnpl_events
        events = scrape_nnpl_events(mode=mode)
    
    elif library == "spl":
        from scrape_spl_events import scrape_spl_events
        events = scrape_spl_events(mode=mode)
    
    elif library == "ppl":
        from scrape_ppl_events import scrape_ppl_events
        events = scrape_ppl_events(mode=mode)
    
    else:
        raise ValueError(f"Unknown library: {library}")

    print(f"✅ Scraped {len(events)} events total.")

    if mode in ["weekly", "monthly"] and library == "vbpl":
        events = filter_events_by_mode(events, mode)
        print(f"📅 {len(events)} events after {mode} filter.")

    if events:
        print("📤 Uploading to Google Sheets...")
        upload_events_to_sheet(
            events,
            mode=mode,
            library=library,
            age_to_categories=(
                NPL_AGE_TO_CATEGORIES if library == "npl"
                else CHPL_AGE_TO_CATEGORIES if library == "chpl"
                else None
            ),
            name_suffix_map=(
                NPL_LIBRARY_NAME_SUFFIXES if library == "npl"
                else CHPL_NAME_SUFFIXES if library == "chpl"
                else None
            )
        )

        export_events_to_csv(library=library)
        print("✅ Done.")
    else:
        print("⚠️ No events to upload.")
