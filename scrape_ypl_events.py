# scrape_ypl_events.py
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE = "https://yorkcountyva.librarycalendar.com"
FEED = f"{BASE}/events/feed/html"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": f"{BASE}/events/month/{datetime.now().year}/{datetime.now().month:02d}",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def _month_bounds(today):
    first = today.replace(day=1)
    if today.month == 12:
        last = datetime(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        last = datetime(today.year, today.month + 1, 1) - timedelta(days=1)
    return first, last

def _sundays_between(start_date, end_date):
    # Find the Sunday on or before start_date
    sunday = start_date - timedelta(days=start_date.weekday() + 1 if start_date.weekday() != 6 else 0)
    # If start_date is Monday(0)→ add 1 day to go back to Sunday(6)
    if start_date.weekday() != 6:
        sunday = start_date - timedelta(days=start_date.weekday() + 1)
    else:
        sunday = start_date  # already Sunday
    # But if that put us before the month too far, it’s fine; backend adjusts with adjust_range=1
    cur = sunday
    while cur <= end_date:
        yield cur
        cur += timedelta(days=7)

def scrape_YPL_events(mode="all"):
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if mode == "weekly":
        start_range = today
        end_range = today + timedelta(days=7)
    elif mode == "monthly":
        start_range, end_range = _month_bounds(today)
    else:
        start_range = today
        end_range = today + timedelta(days=90)

    print("🎯 Scraping YPL events via LibraryCalendar feed (weekly endpoints)…")
    print(f"🧪 mode={mode} | range {start_range.date()} → {end_range.date()}")

    events = []
    seen = set()  # (date_str, link)

    # Loop Sundays across the window; site expects once=calendar-week + current_week
    for week_sunday in _sundays_between(start_range, end_range):
        current_month = f"{week_sunday.year:04d}-{week_sunday.month:02d}"
        current_week = week_sunday.strftime("%Y-%m-%d")
        params = {
            "_wrapper_format": "lc_calendar_feed",
            "once": "calendar-week",
            "current_month": current_month,
            "current_week": current_week,
            "adjust_range": "1",
        }
        print(f"📄 Fetching week feed: {current_week} (month {current_month})")
        r = requests.get(FEED, params=params, headers=HEADERS, timeout=30)
        if r.status_code == 400:
            print(f"⚠️ 400 for week {current_week}; skipping this week.")
            continue
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Per-day buckets within the returned week
        for day in soup.select(".calendar__day--ajax"):
            date_str = day.get("data-date", "").strip()
            if not date_str:
                continue
            try:
                event_date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                continue
            if not (start_range <= event_date <= end_range):
                continue

            for card in day.select(".event-card"):
                a = card.select_one(".lc-event__title a.lc-event__link")
                name = (a.get_text(strip=True) if a else "").strip()
                link = urljoin(BASE, a["href"]) if (a and a.has_attr("href")) else ""

                # dedupe per (date, link)
                key = (date_str, link)
                if key in seen:
                    continue
                seen.add(key)

                time_el = card.select_one(".lc-event-info-item--time")
                time_str = time_el.get_text(strip=True).replace("–", "-") if time_el else ""

                groups_el = card.select_one(".lc-event-info__item--colors")
                ages = groups_el.get_text(" ", strip=True) if groups_el else ""

                loc_el = card.select_one(".lc-event-info__item--categories")
                location = loc_el.get_text(" ", strip=True) if loc_el else ""

                desc_el = card.select_one(".field--name-description")
                description = desc_el.get_text(" ", strip=True) if desc_el else ""

                events.append({
                    "Event Name": name,
                    "Event Link": link,
                    "Event Status": "Available",
                    "Time": time_str,
                    "Ages": ages,
                    "Location": location,
                    "Month": event_date.strftime("%b"),
                    "Day": str(event_date.day),
                    "Year": str(event_date.year),
                    "Event Date": date_str,
                    "Event End Date": date_str,
                    "Event Description": description,
                    "Series": "",
                    "Program Type": "",
                    "Categories": "",
                })

    print(f"✅ Scraped {len(events)} YPL events.")
    return events
