import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from helpers import wJson, rJson
import re
from constants import TITLE_KEYWORD_TO_CATEGORY_RAW

def check_keyword(word, text):
    pattern = rf'\b{re.escape(word)}\b'
    if re.search(pattern, text, re.IGNORECASE):
        return True
    return False

def clean_data(full_data):
    # full_data = rJson('events.json')

    loc_cat = "Event Location - Hampton"
    free_cat = "Audience - Free Event"
    age_cats = [
        "Audience - School Age",
        "Audience - Teens",
        "Audience - Family Event"
    ]

    full_data_new = []

    for i, event in enumerate(full_data):
        categories = set()
        tags = event['Tags']
        tags = [t['tag'] for t in tags]
        if not "Things to Do with Kids" in tags:
            continue

        for keyword, categorie in TITLE_KEYWORD_TO_CATEGORY_RAW.items():
            if check_keyword(keyword.lower(), event['Event Name'].lower()) or check_keyword(keyword, event['Event Description'].lower()):
                categories.add(categorie)

        categories = list(categories)

        full_data[i]['Categories'] = [loc_cat, free_cat]

        if free_cat in categories:
            categories.remove(free_cat)

        full_data[i]['Categories'].extend(age_cats)
        
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

    # Find the main container
    main_div = soup.find('div', class_='tribe-events-calendar-list',
                         attrs={'class': lambda x: isinstance(x, list) and x == ['tribe-events-calendar-list']})
    if not main_div:
        return events

    event_divs = main_div.find_all(
        'div',
        class_='tribe-events-calendar-list__event-row--featured'
    )

    for div in event_divs:
        event = {}
        print("=====================================================")
        time_tag = div.find('time')
        if time_tag and time_tag.has_attr('datetime'):
            # print("date:", time_tag['datetime'])
            event['date'] = time_tag['datetime'].strip()
        
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

        event_series = event_meta_details.find('dd', class_ = 'tec-events-pro-series-meta-detail--link')
        try:
            event['Series'] = event_series.get_text().strip()
            event['Series Link'] = event_series.find('a')['href']
        except:
            event['Series'] = ""
            event['Series Link'] = ""

        event['Tags'] = []
        try:
            event_tags = event_meta_details.find('dd', class_ = 'tribe-event-tags').find_all('a')
            for tag in event_tags:
                event['Tags'].append(
                    {
                        'tag': tag.get_text().strip(),
                        'link': tag['href']
                    }
                )
        except:
            pass

        try:
            event_website = event_meta_details.find('dd', class_ = 'tribe-events-event-url').find('a')['href']
            event['Event Website'] = event_website
        except:
            event['Event Website'] = ""

        event_meta_organizer = event_soup.find('div', class_ = 'tribe-events-meta-group-organizer')


        try:
            event_organizer = event_meta_organizer.find('dd', class_ = 'tribe-organizer')
            event['Organizer'] = event_organizer.get_text().strip()
            event['Organizer Link'] = event_organizer.find('a')['href']
        except:
            event['Organizer'] = ""
            event['Organizer Link'] = ""

        try:
            organizer_phone = event_meta_organizer.find('dd', class_ = 'tribe-organizer-tel')
            event['Organizer Phone'] = organizer_phone.get_text().strip()
        except:
            event['Organizer Phone'] = ""

        try:
            organizer_website = event_meta_organizer.find('dd', class_ = 'tribe-organizer-url')
            event['Organizer Website'] = organizer_website.find('a')['href']
        except:
            event['Organizer Website'] = ""

        event_meta_venue = event_soup.find('div', class_ = 'tribe-events-meta-group-venue')

        try:
            event_venue = event_meta_venue.find('dd', class_ = 'tribe-venue')
            event['Venue'] = event_venue.get_text().strip()
            event['Venue Link'] = event_venue.find('a')['href']
        except:
            event['Venue'] = ""
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
            event['Location'] = event_location.get_text().strip()
            
            # event['Location'] = {
            #     "full": event_location.get_text().strip(),
            # }
            # street_address = event_location.find('span', class_ = 'tribe-street-address')
            # if street_address:
            #     event['Location']['street address'] = street_address.get_text().strip()
            # else:
            #     event['Location']['street address'] = ""
            
            # locality = event_location.find('span', class_ = 'tribe-locality')
            # if locality:
            #     event['Location']['locality'] = locality.get_text().strip()
            # else:
            #     event['Location']['locality'] = ""

            # region = event_location.find('abbr', class_ = 'tribe-region')
            # if region:
            #     event['Location']['region'] = region.get_text().strip()
            #     event['Location']['full region'] = region['title']
            # else:
            #     event['Location']['region'] = ""
            #     event['Location']['full region'] = ""

            # postal_code = event_location.find('span', class_ = 'tribe-postal-code')
            # if postal_code:
            #     event['Location']['postal code'] = postal_code.get_text().strip()
            # else:
            #     event['Location']['postal code'] = ""

            # country_name = event_location.find('span', class_ = 'tribe-country-name')
            # if country_name:
            #     event['Location']['country name'] = country_name.get_text().strip()
            # else:
            #     event['Location']['country name'] = ""

        except:
            # event['Location'] = {}
            event['Location'] = ""
            
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


def scrap_visithampton(mode = "all"):
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
