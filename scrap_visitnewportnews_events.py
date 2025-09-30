from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import requests, json
# import urllib.parse
from helpers import wJson, rJson, infer_age_categories_from_description, normalize_time_from_fields
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

def _norm_time_token(tok: str) -> str:
    t = (tok or "").strip().lower().replace(".", "")
    if t in {"noon", "12 noon"}: return "12:00 PM"
    if t in {"midnight"}:        return "12:00 AM"
    return tok

def _fmt_to_12(s: str) -> datetime:
    s = _norm_time_token(s).upper()
    s = s.replace(".", "").strip()
    if ":" not in s and ("AM" in s or "PM" in s):
        s = s.replace("AM", ":00 AM").replace("PM", ":00 PM")
    return datetime.strptime(s, "%I:%M %p") if ":" in s else datetime.strptime(s, "%I %p")

def fix_time_range(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"\s+to\s+", " - ", s, flags=re.I).strip()
    m = re.match(
        r"^\s*(\d{1,2}(?::\d{2})?)\s*([ap]\.?m\.?)\s*[-–—]\s*(\d{1,2}(?::\d{2})?)\s*([ap]\.?m\.?)?\s*$",
        s, flags=re.I
    )
    if not m:
        return s  # leave unchanged if it doesn’t match

    sh, sm, eh, em = m.groups()
    start = datetime.strptime(f"{sh} {sm}".replace(".", ""), "%I:%M %p" if ":" in sh else "%I %p")
    if em:
        end = datetime.strptime(f"{eh} {em}".replace(".", ""), "%I:%M %p" if ":" in eh else "%I %p")
    else:
        end = datetime.strptime(f"{eh} {start.strftime('%p')}", "%I:%M %p" if ":" in eh else "%I %p")
        if end <= start:
            end = end + timedelta(hours=12)
    return f"{start.strftime('%-I:%M %p')} - {end.strftime('%-I:%M %p')}"

def fix_time_sanity(s: str) -> str:
    """
    If we got '10:00 AM - 5:00 AM' but the source clearly means daytime hours,
    flip the end to PM when start is AM and end<=start.
    """
    m = re.match(r'^\s*(\d{1,2}:\d{2})\s*([AP]M)\s*-\s*(\d{1,2}:\d{2})\s*([AP]M)\s*$', s, re.I)
    if not m:
        return s
    sh, sm, eh, em = m.groups()
    try:
        s_dt = datetime.strptime(f"{sh} {sm.upper()}", "%I:%M %p")
        e_dt = datetime.strptime(f"{eh} {em.upper()}", "%I:%M %p")
        if sm.upper() == "AM" and em.upper() == "AM" and e_dt <= s_dt:
            e_dt = e_dt + timedelta(hours=12)  # assume PM
            return f"{s_dt.strftime('%-I:%M %p')} - {e_dt.strftime('%-I:%M %p')}"
    except Exception:
        pass
    return s

def _parse_api_meridiem(s: str) -> str | None:
    """Return 'AM' or 'PM' if we can infer it from API startTime (12h or 24h)."""
    if not s:
        return None
    t = s.strip()
    # 24h like '14:30:00'
    m24 = re.match(r"^(\d{1,2}):(\d{2})(?::\d{2})?$", t)
    if m24:
        h = int(m24.group(1))
        return "PM" if 12 <= h <= 23 else "AM"
    # 12h like '2:30 PM'
    m12 = re.search(r"\b([AP])M\b", t, re.I)
    if m12:
        return m12.group(0).upper()
    return None

def align_with_api_meridiem(time_str: str, api_start: str) -> str:
    """
    If API says PM but our time_str says AM (or vice-versa), fix it.
    Also handles single times by synthesizing +60 min using the API's meridiem.
    """
    mer = _parse_api_meridiem(api_start)
    if not time_str or not mer:
        return time_str

    # Single time like '2:30 AM' → make a 1h range with API meridiem
    single = re.match(r"^\s*(\d{1,2}:\d{2})\s*([AP]M)\s*$", time_str, re.I)
    if single:
        hhmm = single.group(1)
        start = datetime.strptime(f"{hhmm} {mer}", "%I:%M %p")
        end = start + timedelta(minutes=60)
        return f"{start.strftime('%-I:%M %p')} - {end.strftime('%-I:%M %p')}"

    # Range like '2:30 AM - 3:30 AM' → set both to API meridiem, then bump end if needed
    rng = re.match(r"^\s*(\d{1,2}:\d{2})\s*([AP]M)\s*-\s*(\d{1,2}:\d{2})\s*([AP]M)\s*$", time_str, re.I)
    if rng:
        sh, sm, eh, em = rng.groups()
        s_dt = datetime.strptime(f"{sh} {mer}", "%I:%M %p")
        e_dt = datetime.strptime(f"{eh} {mer}", "%I:%M %p")
        if e_dt <= s_dt:
            e_dt += timedelta(hours=12)  # usual afternoon window
        return f"{s_dt.strftime('%-I:%M %p')} - {e_dt.strftime('%-I:%M %p')}"

    return time_str


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

        # 1) Build time string
        t = normalize_time_from_fields(
            times_text=d.get('times'),
            start_time=d.get('startTime'),
            end_time=d.get('endTime'),
            default_minutes=60
        )
        
        # 2) Normalize separators / odd meridiems ("to", "p.m.", etc.)
        t = fix_time_range(t)
        
        # 3) Sanity flip (AM–AM with end <= start → PM)
        t = fix_time_sanity(t)
        
        # 4) Align with API startTime meridiem (fixes 2:30 AM → 2:30 PM cases)
        t = align_with_api_meridiem(t, d.get('startTime') or "")
        
        d['Time'] = t

        # ---- BEGIN: fix identical start/end ----
        def _fmt_time12(dt):
            # Cross-platform 12h format w/o leading zero
            s = dt.strftime("%I:%M %p")
            return s.lstrip("0")
        
        def _parse_time12(s):
            raw = (s or "").strip().upper()
            # allow "7:00 PM" or "7:00PM"
            raw = raw.replace(" ", "")
            return datetime.strptime(raw, "%I:%M%p")
        
        def _synthesize_range_from(start_str, minutes=60):
            try:
                base = _parse_time12(start_str)
                end  = base + timedelta(minutes=minutes)
                return f"{_fmt_time12(base)} - {_fmt_time12(end)}"
            except Exception:
                return start_str
        
        t = (d.get('Time') or "").strip()
        
        # Case A: already "H:MM AM - H:MM PM" — ensure they're not identical
        m = re.match(r'^\s*(\d{1,2}:\d{2}\s*[AP]M)\s*-\s*(\d{1,2}:\d{2}\s*[AP]M)\s*$', t, re.IGNORECASE)
        if m:
            left, right = m.group(1).strip(), m.group(2).strip()
            try:
                if _parse_time12(left) == _parse_time12(right):
                    st_field = (d.get('startTime') or "").strip()
                    en_field = (d.get('endTime') or "").strip()
                    # If API gave distinct start/end, trust them
                    if st_field and en_field:
                        try:
                            if _parse_time12(st_field) != _parse_time12(en_field):
                                d['Time'] = f"{st_field} - {en_field}"
                            else:
                                d['Time'] = _synthesize_range_from(left, 60)
                        except Exception:
                            d['Time'] = _synthesize_range_from(left, 60)
                    elif st_field:
                        d['Time'] = _synthesize_range_from(st_field, 60)
                    else:
                        d['Time'] = _synthesize_range_from(left, 60)
            except Exception:
                # parsing failed → leave as-is
                pass
        else:
            # Case B: single time like "7:00 PM" → synthesize an end time
            single = re.match(r'^\s*(\d{1,2}:\d{2}\s*[AP]M)\s*$', t, re.IGNORECASE)
            if single:
                d['Time'] = _synthesize_range_from(single.group(1), 60)
        # ---- END: fix identical start/end ----



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



def scrap_day(date_obj, all_fields):
    """Scrap events for a single day (helper for multithreading)."""
    token = get_token()
    start_date = get_right_date(date_obj.date())
    end_date = get_right_date(date_obj.date())
    print(start_date, " - ", end_date)
    url = f"{BASE_URL}/includes/rest_v2/plugins_events_events_by_date/find/"
    
    skip, plus_val = 0, 3
    day_data = []
    while True:
        payload = {
            "filter": {
                "active": True,
                "$and": [
                    {"categories.catId": {
                        "$in": ["9","4","3","6","5","8","12","2","7","1","10"]
                    }}
                ],
                "date_range": {
                    "start": {"$date": start_date},
                    "end": {"$date": end_date}
                }
            },
            "options": {
                "skip": skip,
                "limit": plus_val,
                "count": True,
                "castDocs": False,
                "fields": all_fields,
                "hooks": [],
                "sort": {"date": 1, "rank": 1, "title_sort": 1}
            }
        }
        params = {"json": json.dumps(payload), "token": token}
        response = requests.get(url, headers=HEADERS, cookies=COOKIES, params=params)
        response.raise_for_status()
        responseJson = response.json()

        data = format_data(responseJson)
        if not data:
            break
        day_data.extend(data)
        skip += plus_val
    return day_data


def scrap_visitnewportnews(mode="all", max_workers=10):
    print("start scrapping from visitnewportnews.com ...")
    today = datetime.now(timezone.utc)
    if mode == "weekly":
        date_range_end = today + timedelta(days=7)
    elif mode == "monthly":
        date_range_end = today + timedelta(days=30)
    else:
        date_range_end = today + timedelta(days=90)

    # Prepare fields
    all_fields = set(rJson('all_fields(visitnewportnews).json'))
    all_fields = {field: 1 for field in all_fields}

    # Build list of days to scrape
    dates = []
    cur = today
    while cur <= date_range_end:
        dates.append(cur)
        cur += timedelta(days=1)

    all_data = []
    all_data_unique = set()

    # Threaded scrape while preserving order
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(lambda d: scrap_day(d, all_fields), dates))

    # Merge results in the same order as dates
    for day_data in results:
        for d in day_data:
            url_check = d.get("absoluteUrl") or d.get("url", "")
            unique_entry = f"{url_check}-{d.get('date','')}"
            if unique_entry not in all_data_unique:
                all_data_unique.add(unique_entry)
                all_data.append(d)

    all_data = filter_data(all_data)
    # wJson(all_data, "all_data(visitnewportnews) new.json")
    return all_data


if __name__ == "__main__":
    events_data = scrap_visitnewportnews("all")
    pass
