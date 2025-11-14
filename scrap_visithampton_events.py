import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from helpers import wJson, rJson
import re
from constants import TITLE_KEYWORD_TO_CATEGORY_RAW
from zoneinfo import ZoneInfo
eastern = ZoneInfo("America/New_York")


def check_keyword(word, text):
    pattern = rf'\b{re.escape(word)}\b'
    if re.search(pattern, text, re.IGNORECASE):
        return True
    return False

def clean_data(full_data):
    # full_data = rJson('events.json')

    loc_cat = "Event Location - Hampton"
    free_cat = "Audience - Free Event"
    age_cat = "Audience - Family Event"

    full_data_new = []

    for i, event in enumerate(full_data):
        categories = set()

        # Make Tags optional and normalized
        raw_tags = event.get('Tags') or []
        tags = []
        for t in raw_tags:
            if isinstance(t, dict):
                tags.append((t.get('tag') or '').strip())
            elif isinstance(t, str):
                tags.append(t.strip())

        if not "Things to Do with Kids" in tags:
            continue

        for keyword, categorie in TITLE_KEYWORD_TO_CATEGORY_RAW.items():
            if check_keyword(keyword.lower(), event['Event Name'].lower()) or check_keyword(keyword, event['Event Description'].lower()):
                categories.add(categorie)

        categories = list(categories)

        full_data[i]['Categories'] = [loc_cat, free_cat]

        if free_cat in categories:
            categories.remove(free_cat)

        full_data[i]['Categories'].append(age_cat)
        
        if categories:
            # print(event['Event Link'])
            categories = ", ".join(categories)
            categories = categories.split(', ')
            categories = list(set(categories))
            full_data[i]['Categories'].extend(categories)

        full_data[i]['Categories'] = ", ".join(full_data[i]['Categories'])
        
        full_data_new.append(full_data[i])

    # wJson(full_data_new, 'full_data.json')
        
    return full_data_new

def get_events(soup, date, page_no):
    events = []
    if not soup:
        return events

    # Try multiple containers/row patterns across TEC versions
    rows = soup.select(
        # TEC v6 list view uses <li> rows
        "li.tribe-events-calendar-list__event, "
        # TEC v5/v6 variants
        "div.tribe-events-calendar-list__event-row, "
        "div.tribe-events-calendar-list__event-row--featured, "
        # Some themes wrap as <article> rows
        "article.tribe-events-calendar-list__event"
    )

    if not rows:
        # helpful debug: show notice if present
        notice = soup.select_one(".tribe-events-c-messages__message, .tribe-events-notices")
        msg = notice.get_text(strip=True) if notice else "(no notice found)"
        print(f"⚠️ No event rows detected on page {page_no}. Notice: {msg}")
        return events

    for row in rows:
        event = {}
        print("=====================================================")

        # Date (prefer <time datetime="YYYY-MM-DD">)
        t = row.select_one("time[datetime]")
        if t and t.get("datetime"):
            event_date = t["datetime"].strip()
            event["date"] = event_date
            try:
                dt = datetime.strptime(event_date, "%Y-%m-%d")
                event["Month"] = dt.strftime("%b")
                event["Day"] = str(dt.day)
                event["Year"] = str(dt.year)
            except Exception:
                event["Month"] = event["Day"] = event["Year"] = ""

        # Title + link (be forgiving about wrappers)
        details = row.select_one(
            ".tribe-events-calendar-list__event-details, "
            ".tribe-events-calendar-list__event, "
            ".tribe-events-calendar-list__event-wrapper, "
            "article.tribe-events-calendar-list__event"
        ) or row
        
        h3 = details.find("h3") if details else None
        a = (h3.find("a") if h3 else None) or row.select_one("h3 a, a.tribe-events-calendar-list__event-title-link")
        
        if not a:
            # Nothing we can identify; skip this row safely BEFORE printing
            print("⚠️ Skipping a row on this page: no title/link found.")
            continue
        
        title = a.get_text(strip=True)
        link  = a.get("href", "").strip()
        
        print("Event Name:", title)
        print("Event Link:", link)
        event["Event Name"] = title
        event["Event Link"] = link

        
        # Fetch detail page to get description/time/location
        event_soup = get_soup_from_url(link)
        if not event_soup:
            event["Tags"] = event.get("Tags") or []
            events.append(event)
            continue
        
        # --- Extract & print Event Tags (covers li/span/dd variants) ---
        event["Tags"] = []
        tag_selectors = [
            "li.tribe-events-meta-group-tags a[rel=tag]",                   # <li> group wrapper (common)
            "span.tribe-event-tags.tribe-events-meta-value a[rel=tag]",     # your screenshot
            "dd.tribe-event-tags a[rel=tag]",                               # older TEC markup
        ]
        for css in tag_selectors:
            tag_links = event_soup.select(css)
            if tag_links:
                for tag_a in tag_links:
                    tag_name = tag_a.get_text(strip=True)
                    tag_link = tag_a.get("href", "")
                    if tag_name:
                        event["Tags"].append({"tag": tag_name, "link": tag_link})
                break  # stop on the first selector that worked
        
        if event["Tags"]:
            print("Event Tags:", [t["tag"] for t in event["Tags"]])
        else:
            print("Event Tags: none")
        
        # Description
        desc = event_soup.select_one(
            ".tribe-events-single-event-description, .tribe-events-pro__event-description"
        )
        event["Event Description"] = desc.get_text(strip=True) if desc else ""


        # Time (handle recurring/single variants)
        meta = event_soup.select_one(".tribe-events-meta-group-details, .tribe-events-pro__event-details")
        time_txt = ""
        if meta:
            # recurring time
            span = meta.select_one(".tribe-recurring-event-time")
            if span:
                time_txt = span.get_text(strip=True)
            else:
                start = meta.select_one(".tribe-events-start-time, abbr.tribe-events-start-datetime")
                end = meta.select_one(".tribe-events-end-time, abbr.tribe-events-end-datetime")
                if start:
                    time_txt = start.get_text(strip=True).replace("@", "at")
                if end:
                    et = end.get_text(strip=True).replace("@", "at")
                    time_txt = f"{time_txt} - {et}" if time_txt else et
        event["Time"] = time_txt

        # --- Venue = Location  ---
        venue_group = event_soup.select_one(
            "div.tribe-events-meta-group-venue, "
            "div.tribe-events-meta-group.tribe-events-meta-group-venue"
        )
        
        location_name = ""
        if venue_group:
            # any anchor inside the venue group (first one is the venue name)
            venue_a = venue_group.select_one("a")
            if venue_a:
                location_name = venue_a.get_text(strip=True)
        
        print("Location:", location_name)
        event["Venue"] = location_name


        event["Tags"] = event.get("Tags") or []
        events.append(event)

    return events


def get_soup_from_url(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.RequestException as e:
        print(f"[Error] Failed to fetch {url} - {e}")
        return None


def scrap_visithampton(mode="monthly", cutoff_date=None, **_):
    print("start scrapping from visithampton.com ...")
    today = datetime.now(timezone.utc)
    if mode == "weekly":
        date_range_end = today + timedelta(days=7)
    elif mode == "monthly":
        date_range_end = today + timedelta(days=30)
    else:
        date_range_end = today + timedelta(days=90)

    page_st = 1
    MAX_PAGES = 50
    # date_st = "2025-08-01"
    date_st = today.date()

    all_events = []
    while page_st < MAX_PAGES:
        print("=====================================================")
        print(f"page: {page_st}")
        url = f"https://visithampton.com/events/list/page/{page_st}/?tribe-bar-date={date_st}"
        print(f"url: {url}")
        print("=====================================================")
        soup = get_soup_from_url(url)
        events = get_events(soup, date_st, page_st)
        if len(events) > 0:
            curr_date = datetime.strptime(events[-1]['date'], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if curr_date > date_range_end:
                print("reach date limit, stop scraping...")
                break
        all_events.extend(events)
        # wJson(all_events, 'events.json')
        page_st += 1
    all_events = clean_data(all_events)
    return all_events

if __name__ == "__main__": 
    pass
