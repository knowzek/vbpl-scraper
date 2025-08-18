import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE = "https://yorkcountyva.librarycalendar.com"
FEED = f"{BASE}/events/feed/html"

def _month_iter(start_date, end_date):
    """Yield (year, month) pairs spanning [start_date, end_date]."""
    y, m = start_date.year, start_date.month
    end_key = end_date.year * 12 + end_date.month
    while (y * 12 + m) <= end_key:
        yield y, m
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1

def scrape_YPL_events(mode="all"):
    """
    Scrape York County Public Library (LibraryCalendar) month feeds and
    filter by the requested date range. Uses the 'calendar-month' feed.
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if mode == "weekly":
        start_range = today
        end_range = today + timedelta(days=7)
    elif mode == "monthly":
        # this month (1st .. last day)
        start_range = today.replace(day=1)
        if today.month == 12:
            end_range = datetime(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_range = datetime(today.year, today.month + 1, 1) - timedelta(days=1)
    else:
        start_range = today
        end_range = today + timedelta(days=90)

    print("🎯 Scraping YPL events via LibraryCalendar feed...")
    print(f"🧪 mode={mode} | range {start_range.date()} → {end_range.date()}")

    events = []
    headers = {"User-Agent": "Mozilla/5.0"}

    # Fetch each overlapping month once; filter by [start_range, end_range]
    for year, month in _month_iter(start_range, end_range):
        params = {
            "_wrapper_format": "lc_calendar_feed",
            "once": "calendar-month",
            "current_month": f"{year:04d}-{month:02d}",
            "adjust_range": "1",
        }
        print(f"📄 Fetching month feed: {params['current_month']}")
        r = requests.get(FEED, params=params, headers=headers, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Each day bucket has data-date="YYYY-MM-DD"
        for day in soup.select(".calendar__day--ajax"):
            date_str = day.get("data-date", "").strip()
            if not date_str:
                continue
            try:
                event_date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                continue

            # Filter to requested window
            if not (start_range <= event_date <= end_range):
                continue

            for card in day.select(".event-card"):
                # Title + link
                a = card.select_one(".lc-event__title a.lc-event__link")
                name = (a.get_text(strip=True) if a else "").strip()
                link = urljoin(BASE, a["href"]) if (a and a.has_attr("href")) else ""

                # Time (normalize en-dash)
                time_el = card.select_one(".lc-event-info-item--time")
                time_str = time_el.get_text(strip=True).replace("–", "-") if time_el else ""

                # Age groups / audience chips (comma list)
                groups_el = card.select_one(".lc-event-info__item--colors")
                ages = groups_el.get_text(" ", strip=True) if groups_el else ""

                # Location / room (often the room or branch)
                loc_el = card.select_one(".lc-event-info__item--categories")
                location = loc_el.get_text(" ", strip=True) if loc_el else ""

                events.append({
                    "Event Name": name,
                    "Event Link": link,
                    "Event Status": "Available",
                    "Time": time_str,                         # your exporter will split this
                    "Ages": ages,                             # raw groups; mapping optional
                    "Location": location,
                    "Month": event_date.strftime("%b"),
                    "Day": str(event_date.day),
                    "Year": str(event_date.year),
                    "Event Date": event_date.strftime("%Y-%m-%d"),
                    "Event End Date": event_date.strftime("%Y-%m-%d"),
                    "Event Description": "",                  # feed is teaser-only; detail scrape optional
                    "Series": "",
                    "Program Type": "",
                    # Leave Categories blank; your upload step will enrich/dedupe
                    "Categories": ""
                })

    print(f"✅ Scraped {len(events)} YPL events.")
    return events
