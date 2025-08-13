import requests
import urllib.parse
from helpers import wJson, rJson, infer_age_categories_from_description
import json
from datetime import datetime, timedelta, timezone
import pytz
import re
from constants import TITLE_KEYWORD_TO_CATEGORY_RAW

def check_keyword(word, text):
    pattern = rf'\b{re.escape(word)}\b'
    if re.search(pattern, text, re.IGNORECASE):
        return True
    return False

def get_categories(event, cats_toadd):
    # Always-on tags
    base_tags = ["Event Location - Chesapeake", "Audience - Family Event"]

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
    
def filter_data(data):
    newData = []
    for d in data:
        categories = d['categories']
        scoreSTR = "" 
        cats_toadd = []

        for cat in categories:
            if cat['catName'] == "Family Fun":
                scoreSTR += "Main, "
            if cat['catName'] == "Fishing":
                cats_toadd.append("List - Fishing")

        listing = d.get('listing', {})
        subCategories = listing.get('categories', [])
        for sub in subCategories:
            if sub['subcatname'] == "Family Fun":
                scoreSTR += "sub, "
            if sub['subcatname'] == "Outdoor Recreation":
                cats_toadd.append("Audience - Outdoor Event")
            

            

        if not scoreSTR:
            continue

        d['Event Name'] = d.get('title', '')
        d['Event Description'] = d.get('description', '')

        d['Time'] = d.get('times', '')
        d['Time'] = d['Time'].lower()
        d['Time'] = d['Time'].replace('starting:', '')
        d['Time'] = d['Time'].replace('from:', '')
        d['Time'] = d['Time'].replace('to', '-')
        d['Time'] = d['Time'].replace(' pm', 'pm')
        d['Time'] = d['Time'].replace(' am', 'am').strip()

        d['Location'] = d.get('location', '')
        d['Event Link'] = d.get('absoluteUrl', '')

        date = d['date'].split('-')
        d['Year'] = date[0]
        d['Month'] = date[1]
        d['Day'] = date[2]

        get_categories(d, cats_toadd)

        
        newData.append(d)

    return newData



BASE_URL = "https://www.visitchesapeake.com"

HEADERS = {
    "sec-ch-ua-platform": '"Windows"',
    "Referer": "https://www.visitchesapeake.com/events/",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
    "sec-ch-ua-mobile": "?0"
}

def get_right_date(date):

    client_tz = pytz.timezone("America/New_York")
    # Create date at 00:00 in client's timezone
    date = str(date)
    datelst = date[:10].split('-')
    year = int(datelst[0])
    mon = int(datelst[1])
    day = int(datelst[2])
    client_midnight = client_tz.localize(datetime(year, mon, day, 0, 0, 0))
    # Convert to UTC
    utc_time = client_midnight.astimezone(pytz.UTC)
    # Format as ISO 8601 with milliseconds and 'Z'
    formatted = utc_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return formatted

def get_previous_date(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    prev_date = date_obj - timedelta(days=1)
    return prev_date.strftime("%Y-%m-%d")

def format_data(jsondata):
    docs = jsondata['docs']['docs']
    for doc in docs:
        date_fields = [
            'date',
            'startDate',
            'endDate',
            'nextDate',
            'updated',
        ]
        for date_field in date_fields:
            doc[date_field] = doc.get(date_field, '')[:10]
        try:
            doc['date'] = get_previous_date(doc['date'])
        except:
            pass
        try:
            doc['endDate'] = get_previous_date(doc['endDate'])
        except:
            pass
        if "dates" in doc:
            doc['dates']['eventDate'] = doc['dates'].get('eventDate', '')[:10]
            try:
                doc['dates']['eventDate'] = get_previous_date(doc['dates']['eventDate'])
            except:
                pass
    return docs

def get_token():
    """Fetch the token from the site."""
    url = f"{BASE_URL}/plugins/core/get_simple_token/"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.text.strip()

def scrap_visitchesapeake(mode = "all"):
    print("start scrapping from visitchesapeake.com ...")
    today = datetime.now(timezone.utc)
    if mode == "weekly":
        date_range_end = today + timedelta(days=7)
    elif mode == "monthly":
        date_range_end = today + timedelta(days=30)
    else:
        date_range_end = today + timedelta(days=90)

    all_data = []
    all_data_absoluteUrl = []
    
    while True:
        if today > date_range_end:
            break
        """Fetch events from VisitChesapeake using the token."""
        token = get_token()
        start_date= get_right_date(today.date())
        end_date=get_right_date(today.date() + timedelta(days=7))
        print(start_date, " - ", end_date)
        payload = {
            "filter": {
                "solrOptions": {},
                "categories.catId": {
                    "$in": [
                        "1019","1026","1027","1016","1034","1017","1022","1030","1021",
                        "1023","1038","1020","1025","1018","1024","1032"
                    ]
                },
                "date_range": {
                    "start": {"$date": start_date},
                    "end": {"$date": end_date}
                }
            },
            "options": {
                "skip": 0,
                "limit": 20,
                "hooks": ["afterFind_listing", "afterFind_host"],
                "sort": {"date": 1, "rank": 1, "title": 1},
                "fields": {},
                "count": True
            }
        }

        # Properly encode as JSON then URL encode
        json_payload = json.dumps(payload, separators=(",", ":"))
        encoded_payload = urllib.parse.quote(json_payload)
        events_url = f"{BASE_URL}/includes/rest_v2/plugins_events_events_by_date/find/?json={encoded_payload}&token={token}"
        response = requests.get(events_url, headers=HEADERS)
        response.raise_for_status()
        responseJson = response.json()
        # print(responseJson['docs']['count'])
        data = format_data(responseJson)
        # print(len(data))
        # print("========")
        for d in data:
            if d['absoluteUrl'] in all_data_absoluteUrl:
                continue
            all_data_absoluteUrl.append(d['absoluteUrl'])
            all_data.append(d)

        today = today + timedelta(days=8)

    all_data = filter_data(all_data)
    # wJson(all_data, "all_data.json")
    return all_data


if __name__ == "__main__":
    events_data = scrap_visitchesapeake("all")
    pass

