from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import re, json, requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from helpers import rJson, wJson, infer_age_categories_from_description
from constants import TITLE_KEYWORD_TO_CATEGORY_RAW

# Adult/18+ style filters (word-boundary matches)
ADULT_KEYWORDS = [
    "adult", "adults", "18+", "21+",
    "resume", "job help", "tax help", "yogi", "lecture"
]

def is_likely_adult_event(title: str, description: str) -> bool:
    """
    Returns True if any adult-coded keyword appears in title or description.
    Uses word-boundary regex so 'yoga' doesn't match 'yogurt', etc.
    """
    txt = f"{title or ''} {description or ''}".lower()
    for kw in ADULT_KEYWORDS:
        if re.search(rf"(?<!\w){re.escape(kw)}(?!\w)", txt):
            return True
    return False

def get_next_month(month):
    next_month = month % 12 + 1
    return f"{next_month:02}"


def check_keyword(word, text):
    pattern = rf'\b{re.escape(word)}\b'
    if re.search(pattern, text, re.IGNORECASE):
        return True
    return False

def get_categories(event, cats_toadd):
    # Always-on tags
    base_tags = ["Event Location - Suffolk", "Audience - Family Event"]

    # 1) Keyword-driven tags 
    keyword_tags = set(cats_toadd)
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

def remove_html_entities(text: str) -> str:
    # Remove all entities like &quot; or &#8220; or &#x27;
    return re.sub(r'&[^;\s]+;', '', text)

def get_event_byurl(url):
    # print("getting event:", url)

    event_dict = {}

    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9,ar-JO;q=0.8,ar;q=0.7,ja-JP;q=0.6,ja;q=0.5',
        'priority': 'u=0, i',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
    }

    response = requests.get(url, headers=headers, timeout=15)
    soup2 = BeautifulSoup(response.text, "html.parser")
    event_meta = soup2.find("div", class_="mec-event-meta")

    if event_meta:
        event_date = event_meta.find("div", class_="mec-single-event-date")
        if event_date:
            event_dict['start_date'] = (event_date.find("span", class_="mec-start-date-label") or "").text.strip() if event_date.find("span", class_="mec-start-date-label") else ""
            event_dict['end_date'] = (event_date.find("span", class_="mec-end-date-label") or "").text.replace('-', '').strip() if event_date.find("span", class_="mec-end-date-label") else ""
            event_dict['status'] = (event_date.find("span", class_="mec-holding-status") or "").text.strip() if event_date.find("span", class_="mec-holding-status") else ""

        event_time = event_meta.find("div", class_="mec-single-event-time")
        if event_time:
            time = event_time.find("abbr", class_="mec-events-abbr")
            event_dict['time'] = time.text.strip() if time else ""

        event_organizer = event_meta.find("div", class_="mec-single-event-organizer")
        if event_organizer:
            organizer = event_organizer.find("dd", class_="mec-organizer")
            event_dict['organizer_name'] = organizer.text.strip() if organizer else ""

            organizer_tel = event_organizer.find("dd", class_="mec-organizer-tel")
            if organizer_tel:
                tel = organizer_tel.text.lower().replace("phone", "").strip()
                event_dict['organizer_tel'] = tel
            else:
                event_dict['organizer_tel'] = ""

            organizer_url = event_organizer.find("dd", class_="mec-organizer-url")
            if organizer_url:
                url_text = organizer_url.text.lower().replace("website", "").strip()
                event_dict['organizer_url'] = url_text
            else:
                event_dict['organizer_url'] = ""

    return event_dict


def extract_event_json(script_tag):   
    try:
        return json.loads(script_tag.string)
    except Exception:
        return None

def get_events(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    events = []
    events_final = []

    calendar_div = soup.find("div", id=re.compile(r"^mec-owl-calendar-d-table"))
    days_divs = calendar_div.find_all("div", id=re.compile(r"^mec_daily_view_day"))
    for day_div in days_divs:
        events.append({
            "weekday": day_div.get("data-day-weekday"),
            "monthday": day_div.get("data-day-monthday"),
            "events count": day_div.get("data-events-count"),
            "events": []
        })

    ul_events = soup.find("ul", class_="mec-daily-view-dates-events")
    if not ul_events:
        return

    li_events = ul_events.find_all("li")
    tasks = []
    results = {}

    with ThreadPoolExecutor(max_workers=10) as executor:  # tune workers if needed
        for i, li_event in enumerate(li_events):
            scripts_jsons = li_event.find_all("script", type="application/ld+json")
            for script_json in scripts_jsons:
                event_json = extract_event_json(script_json)
                if not event_json:
                    continue
                # submit threaded fetch
                fut = executor.submit(get_event_byurl, event_json['url'])
                tasks.append((i, event_json, fut))

        for i, event_json, fut in tasks:
            try:
                event_info = fut.result()
            except Exception as e:
                event_info = {}
            # event_json['event_info'] = event_info
            event_json.update(event_info)
            event_json['weekday'] = events[i]['weekday']
            event_json['Event Name'] = remove_html_entities(event_json.get('name', ''))
            event_json['Event Description'] = remove_html_entities(event_json.get('description', ''))
            event_json['Event Status'] = event_json.get('status', '')
            event_json['Time'] = event_json.get('time', '')
            event_json['Event Link'] = event_json.get('url', '')
            date = event_json.get('startDate', '')
            if date != '':
                date = date.split('-')
                event_json['Year'] = date[0]
                event_json['Month'] = date[1]
                event_json['Day'] = date[2]
            
            event_json['Location'] = event_json.get('location', {}).get('name', '')
            event_json['Organizer'] = event_json.get('organizer_name', '')

            price = event_json.get('offers', {}).get('price', '')
            if price == '0':
                cats_toadd = ['Audience - Free Event']
            else:
                cats_toadd = []

            if is_likely_adult_event(event_json['Event Name'], event_json['Event Description']):
                print(f"⏭️ Skipping: Adult/flagged → {event_json['Event Name']}")
                continue
                
            get_categories(event_json, cats_toadd)
            events_final.append(event_json)
            # events[i]['events'].append(event_json)

    return events_final


def scrap_visitsuffolk(mode = "all"):
    print("start scrapping from visitsuffolk.com ...")
    today = datetime.now(timezone.utc)
    if mode == "weekly":
        date_range_end = today + timedelta(days=7)
    elif mode == "monthly":
        date_range_end = today + timedelta(days=30)
    else:
        date_range_end = today + timedelta(days=90)

    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9,ar-JO;q=0.8,ar;q=0.7,ja-JP;q=0.6,ja;q=0.5",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "origin": "https://www.visitsuffolkva.com",
        "referer": "https://www.visitsuffolkva.com/events/",
        "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/138.0.0.0 Safari/537.36"
        ),
        "x-requested-with": "XMLHttpRequest",
    }

    
    events_final_lst = []
    skin="daily",
    event_status="all",
    extra_params=None
    url = "https://www.visitsuffolkva.com/wp-admin/admin-ajax.php"
    month=today.strftime("%m")
    year=str(today.year)
    prev_month = month
    while True:
        if int(prev_month) > int(month):
            year = str(int(year) + 1)

        data = {
            "action": "mec_full_calendar_switch_skin",
            "skin": skin,
            "atts[sk-options][monthly_view][style]": "classic",
            "atts[sk-options][timetable][style]": "modern",
            "atts[sk-options][list][style]": "classic",
            "atts[sk-options][grid][style]": "classic",
            "atts[id]": "946",
            "sf[s]": "",
            "sf[address]": "",
            "sf[cost-min]": "",
            "sf[cost-max]": "",
            "sf[time-start]": "",
            "sf[time-end]": "",
            "sf[month]": month,
            "sf[year]": year,
            "sf[start]": "",
            "sf[end]": "",
            "sf[category]": "",
            "sf[location]": "",
            "sf[organizer]": "",
            "sf[speaker]": "",
            "sf[tag]": "",
            "sf[label]": "",
            "sf[event_type]": "",
            "sf[event_type_2]": "",
            "sf[event_status]": event_status,
            "sf[attribute]": "",
            "apply_sf_date": "1",
            "sed": "0",
        }

        # allow user to inject extra parameters
        if extra_params:
            data.update(extra_params)

        response = requests.post(url, headers=headers, data=data)

        if response.status_code == 200:
            events_lst = get_events(response.text)
            for event in events_lst:
                event_startDate = event['startDate']
                date_obj = datetime.strptime(event_startDate, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if date_obj < today:
                    continue
                if date_obj > date_range_end:
                    return events_final_lst
                events_final_lst.append(event)
        else:
            raise Exception(f"Request failed [{response.status_code}]: {response.text[:200]}")
        prev_month = month
        month = get_next_month(int(month))

# Example usage
if __name__ == "__main__":
    events = scrap_visitsuffolk('all')
    # wJson(events, "events.json")
    pass

