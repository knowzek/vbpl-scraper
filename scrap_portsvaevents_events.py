import requests, time, requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from helpers import wJson, rJson, infer_age_categories_from_description
import re
from constants import TITLE_KEYWORD_TO_CATEGORY_RAW

def fetch_event_page(url: str, *, retries: int = 5, timeout: int = 25) -> BeautifulSoup | None:
    for i in range(retries):
        try:
            resp = requests.get(url, timeout=timeout, headers={"User-Agent":"Mozilla/5.0"})
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            wait = i + 1
            print(f"[Error] Failed to fetch {url} - {e}\ntry again after {wait} sec...")
            time.sleep(wait)
    print(f"[Skip] Giving up on {url} after {retries} retries.")
    return None

def _first_text(root: BeautifulSoup, selectors: list[str], replace_at=True) -> str:
    if not root:
        return ""
    for sel in selectors:
        el = root.select_one(sel)
        if el:
            txt = el.get_text(strip=True)
            return txt.replace("@", "at") if replace_at else txt
    return ""

def _is_all_day(card: BeautifulSoup) -> bool:
    # TEC marks all-day items with a variety of classes depending on theme
    classes = " ".join(card.get("class", [])).lower()
    return ("all-day" in classes) or bool(card.select_one(".tribe-events-calendar-list__event--all-day, .tribe-events-event-meta--all-day"))


def is_too_late(time_str: str) -> bool:
    """
    Return True if the event ends at 7:00 PM or later.
    Works with formats like:
      "6:00 PM - 7:30 PM"
      "7:00 PM"
      "All Day Event" (treated as allowed)
    """
    if not time_str or "all day" in time_str.lower():
        return False

    # Split on dash, take the END if available
    parts = re.split(r"\s*[-–—]\s*", time_str)
    end_part = parts[1] if len(parts) > 1 else parts[0]

    try:
        end_time = datetime.strptime(end_part.strip(), "%I:%M %p")
    except ValueError:
        try:
            end_time = datetime.strptime(end_part.strip(), "%I %p")
        except ValueError:
            return False  # skip filtering if parsing fails

    # Compare against 7:00 PM
    cutoff = datetime.strptime("7:00 PM", "%I:%M %p")
    return end_time >= cutoff



def check_keyword(word, text):
    pattern = rf'\b{re.escape(word)}\b'
    if re.search(pattern, text, re.IGNORECASE):
        return True
    return False

def get_categories(event):
    # Always-on tags
    base_tags = ["Event Location - Portsmouth", "Audience - Family Event"]

    # 1) Keyword-driven tags 
    keyword_tags = set()
    for keyword, categorie in TITLE_KEYWORD_TO_CATEGORY_RAW.items():
        if check_keyword(keyword.lower(), event['Event Name'].lower()) or check_keyword(keyword, event['Event Description'].lower()):
            keyword_tags.add(categorie)

    flat_keyword_tags = []
    for c in keyword_tags:
        flat_keyword_tags.extend([x.strip() for x in str(c).split(",") if x.strip()])

    # 2) Age-based tags from description
    age_info = infer_age_categories_from_description(event.get("Event Description", ""))
    age_tags = [x.strip() for x in (age_info.get("categories") or "").split(",") if x.strip()]

    # 3) Merge → dedupe
    tags = []
    for group in (base_tags, flat_keyword_tags, age_tags):
        for t in group:
            if t and t not in tags:
                tags.append(t)

    event["Categories"] = ", ".join(tags)

def get_events(soup, date, page_no):

    events = []

    # Find the main container
    main_div = soup.find('div', class_='tribe-events-calendar-list',
                         attrs={'class': lambda x: isinstance(x, list) and x == ['tribe-events-calendar-list']})
    if not main_div:
        return events

    event_divs = main_div.find_all(
        'div',
        class_='tribe-events-calendar-list__event-row'
    )

    for div in event_divs:
        event = {}
        print("=====================================================")
        time_tag = div.find('time')
        if time_tag and time_tag.has_attr('datetime'):
            event_date = time_tag['datetime'].strip()
            event['date'] = event_date
        
            try:
                dt = datetime.strptime(event_date, "%Y-%m-%d")
                event['Month'] = dt.strftime("%b")   # e.g., "Aug"
                event['Day'] = str(dt.day)           # e.g., "11"
                event['Year'] = str(dt.year)         # e.g., "2025"
            except Exception:
                event['Month'] = event['Day'] = event['Year'] = ""

        
        event_wrapper = div.find('div', class_='tribe-events-calendar-list__event-wrapper')
        event_details = event_wrapper.find('div', class_='tribe-events-calendar-list__event-details')
        h3_tag = event_details.find('h3')
        title = h3_tag.get_text().strip()
        link = h3_tag.find('a')['href']

        print("Event Name:", title)
        event['Event Name'] = title

        print("Event Link: ", link)
        event['Event Link'] = link

        event_soup = fetch_event_page(link)  # retries + headers
        time.sleep(0.1)
        
        if event_soup is None:
            # mark and continue so one bad page doesn't kill the batch
            event['Status'] = 'Unavailable'
            event['Event Description'] = ''
            event['Time'] = event.get('Time', '')
            events.append(event)
            continue
        
        # null-safe description
        event_description = _first_text(
            event_soup,
            [
                "div.tribe-events-single-event-description",
                "div.tribe-events-content",
                "div.tribe-events-single-event-content",
                "article .entry-content",
            ],
            default=""
        )
        event['Event Description'] = event_description


        # Prefer the details group, but fall back to the whole page if it's missing
        event_meta_details = event_soup.find('div', class_='tribe-events-meta-group-details') or event_soup
        
        # Try several known locations for start time
        event_time = _first_text(event_meta_details, [
            "div.tribe-recurring-event-time",
            "div.tribe-events-start-time",
            "abbr.tribe-events-start-datetime",
            "div.tribe-event-date-start",
            ".tribe-events-calendar-list__event-time",
            "time"
        ])
        
        # All-day fallback
        if not event_time and _is_all_day(event_soup):
            event_time = "All Day"
        
        # Optional: append end time if present and meaningful
        event_endtime = _first_text(event_meta_details, [
            "abbr.tribe-events-end-datetime",
            "div.tribe-events-end-time",
            ".tribe-events-calendar-list__event-time-end",
        ])
        
        if event_time and event_endtime and "All Day" not in event_time and event_endtime not in event_time:
            event_time = f"{event_time} - {event_endtime}"
        
        event['Time'] = event_time or ""



        try:
            event_website = event_meta_details.find('dd', class_ = 'tribe-events-event-url').find('a')['href']
            event['Event Website'] = event_website
        except:
            event['Event Website'] = ""


        event_meta_venue = event_soup.find('div', class_ = 'tribe-events-meta-group-venue')

        try:
            event_venue = event_meta_venue.find('dd', class_ = 'tribe-venue')
            event['Venue'] = event_venue.get_text().strip()
            event['Location'] = event_venue.get_text().strip()
        except:
            event['Venue'] = ""
            event['Location'] = ""
        
        try:
            event['Venue Link'] = event_venue.find('a')['href']
        except:
            event['Venue Link'] = ""

        try:
            venue_website = event_meta_venue.find('dd', class_ = 'tribe-venue-url')
            event['Venue Website'] = venue_website.find('a')['href']
        except:
            event['Venue Website'] = ""

        try:
            venue_phone = event_meta_venue.find('dd', class_ = 'tribe-venue-tel')
            event['Venue Phone'] = venue_phone.get_text().strip()
        except:
            event['Venue Phone'] = ""

        


        try:
            event_location = event_meta_venue.find('dd', class_ = 'tribe-venue-location')
            event['old_location'] = event_location.get_text().strip()
        except:
            event['old_location'] = ""
            

        get_categories(event)
        # ⏭️ Skip events ending 7pm or later
        if is_too_late(event.get("Time", "")):
            print(f"⏭️ Skipping late event → {event['Event Name']} ({event['Time']})")
            continue

        # === Block specific venues before appending ===
        BLOCKED_VENUES = [
            "Momac Brewing Company",
            "Sound Bar at Rivers Casino",
            "Roger Browns Restaurant and Sports Bar",
            "Roger Brown's Restaurant and Sports Bar",
            "Baron’s Pub Portsmouth",
            "Harbor Park Stadium",
        ]
        
        loc = (event.get("Location") or "").strip()
        if any(v.lower() in loc.lower() for v in BLOCKED_VENUES):
            print(f"⏭️ Skipping event at blocked venue: {loc} → {event.get('Event Name')}")
            continue
            
        events.append(event)

        # wJson(events, f'jsons/events({date})(page {page_no}).json')


    return events

def get_soup_from_url(url, retrys=5):
    if retrys == 0:
        return None
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.RequestException as e:
        print(f"[Error] Failed to fetch {url} - {e}")
        print(f"try again after {6-retrys} sec...")
        time.sleep(6-retrys)
        return get_soup_from_url(url, retrys -1)


def scrap_portsvaevents(mode="all", cutoff_date=None, **kwargs):
    print("start scrapping from portsvaevents.com ...")
    """
    mode: "all" | "weekly" | "monthly"
    cutoff_date: datetime.date or None (stop once events exceed this)
    """
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

    all_events = []
    while page_st < MAX_PAGES:
        date_st = today.date()
        print("=====================================================")
        print(f"page: {page_st}")
        url = f"https://portsvaevents.com/events/list/page/{page_st}/?tribe-bar-date={date_st}"
        print(f"url: {url}")
        print("=====================================================")
        soup = get_soup_from_url(url)
        events = get_events(soup, date_st, page_st)
        if len(events) > 0:
            tmp_date = datetime.strptime(events[-1]['date'], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            for event in events:
                curr_date = event['date']
                if curr_date == str(date_st):
                    all_events.append(event)
                else:
                    today = today + timedelta(days=1)
                    page_st = 0
                    break
            if tmp_date > date_range_end:
                print("reach date limit, stop scraping...")
                break
        # all_events.extend(events)
        page_st += 1
        time.sleep(0.1)
    # wJson(all_events, 'events.json')
    return all_events

if __name__ == "__main__": 
    # scrap_portsvaevents("weekly")
    pass
