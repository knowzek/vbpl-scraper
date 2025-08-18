import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from helpers import wJson, rJson, infer_age_categories_from_description
import re
from constants import TITLE_KEYWORD_TO_CATEGORY_RAW


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

        event_soup = get_soup_from_url(link)

        # event_schedule = event_soup.find('div', class_ = 'tribe-events-schedule')
        # event_date_start = event_schedule.find('span', class_ = 'tribe-event-date-start').get_text().strip()
        # event_time = event_schedule.find('span', class_ = 'tribe-event-time').get_text().strip()
        
        event_description = event_soup.find('div', class_ = 'tribe-events-single-event-description').get_text().strip()
        event['Event Description'] = event_description

        event_meta_details = event_soup.find('div', class_ = 'tribe-events-meta-group-details')

        try:
            event_time = event_meta_details.find('div', class_ = 'tribe-recurring-event-time').get_text().strip()
        except:
            try:
                event_time = event_meta_details.find('div', class_ = 'tribe-events-start-time').get_text().strip()
            except:
                event_time = event_meta_details.find('abbr', class_ = 'tribe-events-start-datetime').get_text().strip().replace("@", "at")
                try:
                    event_endtime = event_meta_details.find('abbr', class_ = 'tribe-events-end-datetime').get_text().strip().replace("@", "at")
                    event_time += f" - {event_endtime}"
                except:
                    pass

        event['Time'] = event_time


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

        events.append(event)

        # wJson(events, f'jsons/events({date})(page {page_no}).json')


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


def scrap_portsvaevents(mode = "all"):
    print("start scrapping from portsvaevents.com ...")
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
        url = f"https://portsvaevents.com/events/list/page/{page_st}/?tribe-bar-date={date_st}"
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
        page_st += 1
    # wJson(all_events, 'events.json')
    return all_events

if __name__ == "__main__": 
    scrap_portsvaevents("all")
    pass
