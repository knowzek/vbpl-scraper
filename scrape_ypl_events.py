# scrape_ypl_events.py
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

BASE = "https://yorkcountyva.librarycalendar.com"
FEED = f"{BASE}/events/feed/html"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
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
    # Sunday = 6 (Mon=0 ... Sun=6)
    offset = (start_date.weekday() + 1) % 7
    first_sunday = start_date - timedelta(days=offset) if offset else start_date
    cur = first_sunday
    while cur <= end_date:
        yield cur
        cur += timedelta(days=7)

def scrape_YPL_events(mode="all"):
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if mode == "weekly":
        start_range = today
        end_range = today + timedelta(days=7)
    elif mode == "monthly":
        start_range = today
        end_range = today + timedelta(days=30)
    else:
        start_range = today
        end_range = today + timedelta(days=90)

    print("🎯 Scraping YPL events via LibraryCalendar feed (weekly endpoints)…")
    print(f"🧪 mode={mode} | range {start_range.date()} → {end_range.date()}")

    events = []
    seen = set()  # (date_str, link)

    def _strip_disclaimer(text: str) -> str:
        # Remove anything starting at a "Disclaimer(s)" heading if it appears
        parts = re.split(r"\bDisclaimer\(s\)\b", text, flags=re.I)
        return parts[0].strip() if parts else text

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

        headers = dict(HEADERS)  # copy base headers
        headers["Referer"] = f"{BASE}/events/month/{week_sunday.year}/{week_sunday.month:02d}"
        r = requests.get(FEED, params=params, headers=headers, timeout=30)

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

                # Prefer the teaser/description on the card (not the disclaimer)
                desc_el = (
                    card.select_one(".lc-event__teaser")
                    or card.select_one(".lc-event__description")
                    or card.select_one(".field--name-body")
                    or card.select_one(".field--name-description")
                )
                description = desc_el.get_text(" ", strip=True) if desc_el else ""
                description = _strip_disclaimer(description)
                
                # If empty or still looks like a disclaimer, fetch detail page and pull body
                looks_like_disclaimer = (
                    bool(re.search(r"\bDisclaimer\(s\)\b", description, flags=re.I))
                    or description.lower().startswith(("we cannot guarantee", "this program is designed"))
                )
                
                if (not description) or looks_like_disclaimer:
                    try:
                        detail_headers = dict(HEADERS)
                        # give the detail request a sane referer to mimic browser flow
                        detail_headers["Referer"] = f"{BASE}/events"
                        dr = requests.get(link, headers=detail_headers, timeout=30)
                        if dr.ok:
                            dsoup = BeautifulSoup(dr.text, "html.parser")
                            body_el = (
                                dsoup.select_one(".field--name-body")
                                or dsoup.select_one(".lc-event__description")
                                or dsoup.select_one(".node--type-event .field--name-body")
                            )
                            if body_el:
                                description = _strip_disclaimer(body_el.get_text(" ", strip=True))
                    except Exception:
                        pass
                
                clean_description = description


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
                    "Event Description": clean_description,
                    "Series": "",
                    "Program Type": "",
                    "Categories": "",
                })

    print(f"✅ Scraped {len(events)} YPL events.")
    return events
