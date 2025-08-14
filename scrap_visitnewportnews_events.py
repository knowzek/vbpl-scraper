import requests
import urllib.parse
from helpers import wJson, rJson, infer_age_categories_from_description, normalize_time_string
import json
from datetime import datetime, timedelta, timezone
import pytz
import re
from constants import TITLE_KEYWORD_TO_CATEGORY_RAW

BASE_URL = "https://www.visitnewportnews.com"

HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9,ar-JO;q=0.8,ar;q=0.7,ja-JP;q=0.6,ja;q=0.5",
    "Connection": "keep-alive",
    "Referer": "https://www.visitnewportnews.com/events-and-festivals/?bounds=false&view=list&sort=date",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "no-cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"'
}

COOKIES = {
    "_gcl_au": "1.1.2020751759.1755033011",
    "_ga": "GA1.1.883793126.1755033011",
    "mf_user": "23b3d7b3aaf368633699f19b0049cd25|",
    "_clck": "3rmf|2|fye|0|2050",
    "_ga_P8XF0KKXWG": "GS2.1.s1755033011$o1$g1$t1755033053$j18$l0$h64601396",
    "mf_454c89a0-dd9b-4fd5-b442-c552eca72981": "d8e4c55d1384ad86fb2de67b6b2d1ed4|08131189f86cd595ca69dcc6de3f40f24c8f92c7.654055855.1755033011597$0813346109643aafcbd84f52db2f51c0ce3729af.654055855.1755033034863$081353658eda3a3c8f881173a0cad2006f413ec5.654055855.1755033053669|1755033044972||2||||0|18.34|86.73178|0|",
    "_ga_Z9MN82YTMQ": "GS2.1.s1755033011$o1$g1$t1755033053$j18$l0$h0",
    "_ga_Q3027Z5YJW": "GS2.1.s1755033014$o1$g1$t1755033054$j20$l0$h0",
    "_clsk": "y5y2zn|1755033054713|3|1|s.clarity.ms/collect"
}

# def extract_times(text):
#    pattern = r'\b(?:0?[1-9]|1[0-2])(?:\:[0-5][0-9])?(?:am|pm)\b'
#    lst = re.findall(pattern, text, re.IGNORECASE)
#    for i,t in enumerate(lst):
#        if ':' not in t:
#            lst[i] = t[:-2] + ':00' + t[-2:]
#    return lst

def check_keyword(word, text):
    pattern = rf'\b{re.escape(word)}\b'
    if re.search(pattern, text, re.IGNORECASE):
        return True
    return False

def get_categories(event, cats_toadd):
    # Always-on tags
    base_tags = ["Event Location - Newport News", "Audience - Family Event"]

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
            if cat['catName'] == "Family Friendly":
                scoreSTR += "Main, "
            if cat['catName'] == "Fishing":
                cats_toadd.append("List - Fishing")

        listing = d.get('listing', {})
        subCategories = listing.get('categories', [])
        for sub in subCategories:
            if sub['subcatname'] == "Family Friendly":
                scoreSTR += "sub, "
            if sub['subcatname'] == "Outdoor Recreation":
                cats_toadd.append("Audience - Outdoor Event")
            

            

        if not scoreSTR:
            continue

        if "free" in d.get('admission', '').lower():
            cats_toadd.append("Audience - Free Event")

        d['Event Name'] = d.get('title', '')
        d['Event Description'] = d.get('description', '')

        # Build a raw time string from available fields
        raw_time = (d.get('times') or d.get('startTime') or "").strip()
        
        prepped = (raw_time
                   .replace("Starting:", "")
                   .replace("starting:", "")
                   .replace("From:", "")
                   .replace("from:", "")
                   .strip())
        
        # If the API also gives an explicit end time, include it;
        # the helper will recognize it's already a range and just normalize.
        if d.get('endTime'):
            time_str = f"{prepped} - {d['endTime']}"
        else:
            time_str = prepped
        
        # One source of truth: normalize to "H:MM AM - H:MM PM" (or leave as-is if unparseable/All Day)
        d['Time'] = normalize_time_string(time_str)  # default +60 min if only one time found

        d['Location'] = d.get('location', '')
        d['Event Link'] = d.get('absoluteUrl', '')

        date = d['date'].split('-')
        d['Year'] = date[0]
        d['Month'] = date[1]
        d['Day'] = date[2]

        get_categories(d, cats_toadd)

        
        newData.append(d)

    return newData

def get_token():
    """Fetch the token from the site."""
    url = f"{BASE_URL}/plugins/core/get_simple_token/"
    headers = {
        "sec-ch-ua-platform": '"Windows"',
        "Referer": "https://www.visitnewportnews.com/events-and-festivals/?bounds=false&view=list&sort=date",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        "sec-ch-ua-mobile": "?0"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.text.strip()

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


def scrap_visitnewportnews(mode = "all"):
    print("start scrapping from visitnewportnews.com ...")
    today = datetime.now(timezone.utc)
    if mode == "weekly":
        date_range_end = today + timedelta(days=7)
    elif mode == "monthly":
        date_range_end = today + timedelta(days=30)
    else:
        date_range_end = today + timedelta(days=90)

    all_data = []
    all_data_unique = []
    all_fields = set(rJson('all_fields(visitnewportnews).json'))
    all_fields = {field : 1 for field in all_fields}



    while True:
        if today > date_range_end:
            break
        """Fetch events from VisitChesapeake using the token."""
        token = get_token()
        start_date= get_right_date(today.date())
        end_date=get_right_date(today.date() + timedelta(days=7))

        print(start_date, " - ", end_date)
        url = f"{BASE_URL}/includes/rest_v2/plugins_events_events_by_date/find/"
        skip = 0
        while True:

            payload = {
                "filter": {
                    "active": True,
                    "$and": [
                        {
                            "categories.catId": {
                                "$in": [
                                    "9",
                                    "4",
                                    "3",
                                    "6",
                                    "5",
                                    "8",
                                    "12",
                                    "2",
                                    "7",
                                    "1",
                                    "10"
                                ]
                            }
                        }
                    ],
                    "date_range": {
                        "start": {
                            "$date": start_date
                        },
                        "end": {
                            "$date": end_date
                        }
                    }
                },
                "options": {
                    "skip": skip,
                    "limit": 3,
                    "count": True,
                    "castDocs": False,
                    "fields": all_fields,
                    "hooks": [],
                    "sort": {
                        "date": 1,
                        "rank": 1,
                        "title_sort": 1
                    }
                }
            }
            
            skip += 3
            
            params = {
                "json": json.dumps(payload),
                "token": token
            }

            response = requests.get(url, headers=HEADERS, cookies=COOKIES, params=params)
            response.raise_for_status()
            responseJson = response.json()

            data = format_data(responseJson)
            if len(data) == 0:
                break
            for d in data:
                url_check = d.get("absoluteUrl", "")
                if url_check == "":
                    url_check = d.get("url", "")
                unique_entry = f"{url_check}-{d.get("date", "")}"
                if unique_entry in all_data_unique:
                    continue
                all_data_unique.append(unique_entry)
                all_data.append(d)
        
        today = today + timedelta(days=8)

    all_data = filter_data(all_data)
    # wJson(all_data, "all_data(visitnewportnews).json")
    return all_data

    

    

if __name__ == "__main__":
    events_data = scrap_visitnewportnews("all")
    pass
