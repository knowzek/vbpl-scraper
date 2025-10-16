from datetime import datetime, timedelta
import os
import gspread
from google.oauth2 import service_account
import traceback
from config import get_library_config
import json
import re
from constants import LIBRARY_CONSTANTS, TITLE_KEYWORD_TO_CATEGORY, UNWANTED_TITLE_KEYWORDS
from constants import COMBINED_KEYWORD_TO_CATEGORY

import pandas as pd

# === MASTER SHEET OVERRIDE ===
USE_MASTER_SHEET = True  # <— turn on the single-sheet world
MASTER_SPREADSHEET_ID = os.environ.get("MASTER_SPREADSHEET_ID")  # preferred
MASTER_SPREADSHEET_NAME = os.environ.get("MASTER_SPREADSHEET_NAME", "Master Events")  # fallback by name
MASTER_WORKSHEET_NAME = os.environ.get("MASTER_WORKSHEET_NAME", "Master Events")
MASTER_LOG_WORKSHEET_NAME = os.environ.get("MASTER_LOG_WORKSHEET_NAME", "Master Events Log")  # optional


# --- protect a single label that contains commas so we don't split it ---
SPECIAL_MULTIWORD = "List - Cosplay, Anime, Comics"
PLACEHOLDER = "LIST_COSPLAY_ANIME_COMICS"  # something that will never appear naturally

SYNTHESIZE_SINGLE_FOR = {"visitchesapeake", "visitnewportnews", "visitnorfolk", "visityorktown"}
PLACEHOLDER_1159_FOR = {"visitnorfolk", "visityorktown"}
ENFORCE_VENUE_MAP_FOR = {"visitchesapeake", "visityorktown", "visitnorfolk", "visitsuffolk", "vbpr", "visithampton", "visitnewportnews", "portsvaevents"}

DASH_SPLIT = re.compile(r"\s+[-–—]\s+")  # space + dash + space (handles -, – , —)

def _strip_halloween_from_late_events(month: str, tags: list[str]) -> list[str]:
    """
    If the event is in November or December, strip any Halloween-related tags.
    """
    m = (month or "").strip().lower()
    if m in ["nov", "november", "dec", "december"]:
        filtered = []
        for t in tags:
            if not re.search(r"halloween", t, re.I):
                filtered.append(t)
        return filtered
    return tags

def _strip_storytime_for_open_play(title: str, tags: list[str]) -> list[str]:
    """
    If the title contains 'open play', remove any Storytimes tag the
    pipeline might have added from Program Type or keyword hits.
    """
    t = (title or "").lower()
    if re.search(r"\bopen\s*play\b", t):  # matches 'Open Play', 'open-play', 'open  play'
        return [c for c in tags if not re.search(r"\bList\s*-\s*Storytimes\b", c, re.I)]
    return tags


def _strip_room_suffix(loc: str) -> str:
    """
    'Russell Memorial Library - Activity Room, Atrium' → 'Russell Memorial Library'
    """
    base = (loc or "").strip()
    if not base:
        return ""
    # split once on the first " - " (or –/—) and take the left side
    return DASH_SPLIT.split(base, 1)[0].strip()

def _coerce_ymd(year, month, day):
    """Return (y,m,d) where month can be '10', 'Oct', or 'October'; missing parts → None."""
    def _to_int(x):
        try:
            return int(str(x))
        except Exception:
            return None

    y = _to_int(year)
    d = _to_int(day)

    m = None
    if month is not None:
        s = str(month).strip()
        m = _to_int(s)
        if m is None:
            for fmt in ("%b", "%B"):
                try:
                    m = datetime.strptime(s, fmt).month
                    break
                except Exception:
                    pass
    return y, m, d

def _synthesize_one_hour_range(start_str: str, year=None, month=None, day=None, minutes: int = 60) -> str:
    """
    'H[:MM] AM/PM' → 'H:MM AM/PM - H:MM AM/PM', anchored to the row date (handles Oct/October).
    """
    s = (start_str or "").strip().upper().replace(".", "")
    try:
        tod = datetime.strptime(s, "%I:%M %p")
    except ValueError:
        tod = datetime.strptime(s, "%I %p")

    y, m, d = _coerce_ymd(year, month, day)
    if y and m and d:
        anchor = datetime(y, m, d, tod.hour, tod.minute)
    else:
        today = datetime.today()
        anchor = datetime(today.year, today.month, today.day, tod.hour, tod.minute)

    end = anchor + timedelta(minutes=minutes)

    def _fmt12(dt):
        return dt.strftime("%I:%M %p").lstrip("0")

    return f"{_fmt12(anchor)} - {_fmt12(end)}"



def _protect_special_labels(text: str) -> str:
    return (text or "").replace(SPECIAL_MULTIWORD, PLACEHOLDER)

def _restore_special_labels(text: str) -> str:
    return (text or "").replace(PLACEHOLDER, SPECIAL_MULTIWORD)

def _strip_preschool_for_just2s(title: str, tags: list[str]) -> list[str]:
    """
    If the title contains any 'Just 2s' variant, forcibly remove preschool audience tags.
    """
    t = (title or "").lower()
    # matches: "just 2s", "just 2's", "just 2’s", "just twos", "just two's"
    if re.search(r"\bjust\s*(?:2\s*[’']?\s*s|two[’']?s)\b", t):
        return [c for c in tags if c not in {"Audience - Preschool Age", "Audience - Preschool"}]
    return tags

def _strip_schoolage_for_3splease(title: str, tags: list[str]) -> list[str]:
    """
    If the title contains any '3s Please' variant, forcibly remove school-age audience tags.
    """
    t = (title or "").lower()
    # matches: "3s please", "3's please", "three's please"
    if re.search(r"\b3\s*[’']?\s*s\s*please\b|\bthree[’']?s\s*please\b", t):
        return [c for c in tags if c not in {"Audience - School Age"}]
    return tags

def _ensure(lst, item):
    if item not in lst:
        lst.append(item)

def has_audience_tag(tags):
    return any("Audience -" in tag for tag in tags)

def _has_unwanted_title(title: str) -> bool:
    t = (title or "").lower()
    for kw in UNWANTED_TITLE_KEYWORDS:
        # whole-word, case-insensitive match
        if re.search(rf"\b{re.escape(kw.lower())}\b", t):
            return True
    return False

TIME_OK = re.compile(r"\b\d{1,2}(:\d{2})?\s*[ap]m\b", re.I)

DAY_WORD = r"(?:mon(?:day)?|tue(?:sday)?|wed(?:nesday)?|thu(?:rsday)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?)"
_DAY_IDX = {"mon":0,"tue":1,"wed":2,"thu":3,"fri":4,"sat":5,"sun":6}

def _wk_from_ymd(y, m, d):
    try:
        yy = int(y)
        # allow '10', 'Oct', 'October'
        try:
            mm = int(m)
        except Exception:
            mm = datetime.strptime(str(m)[:3], "%b").month
        dd = int(d)
        return datetime(yy, mm, dd).weekday()
    except Exception:
        return None


def _day_idx(tok: str):
    return _DAY_IDX.get(tok[:3].lower())

def _segment_dayset(seg: str):
    s = seg.lower()
    if "daily" in s or "every day" in s:
        return set(range(7))
    days = set()
    if "weekend" in s:
        days.update({5, 6})
    if "weekday" in s:
        days.update({0,1,2,3,4})
    # ranges like "tuesday-friday"
    for a, b in re.findall(rf"\b({DAY_WORD})\s*[-–]\s*({DAY_WORD})\b", s):
        ia, ib = _day_idx(a), _day_idx(b)
        if ia is not None and ib is not None:
            if ia <= ib:
                days.update(range(ia, ib+1))
            else:  # wrap-around, e.g., sat-mon
                days.update(list(range(ia,7)) + list(range(0,ib+1)))
    # singular/plural days like "Saturdays", "Sunday"
    for tok in re.findall(rf"\b{DAY_WORD}s?\b", s):
        i = _day_idx(tok)
        if i is not None:
            days.add(i)
    return days

def _fmt_one_time(p: str) -> str:
    x = (p or "").strip().lower().replace(".", "")
    if x in {"noon","12 noon"}: return "12:00 PM"
    if x == "midnight":         return "12:00 AM"
    # 3p / 3 p → 3:00 pm
    x = re.sub(r"\b(\d{1,2})\s*([ap])\b", r"\1:00 \2m", x)
    # ensure space before am/pm, drop leading zero hour
    x = re.sub(r"(\d)([ap]m)\b", r"\1 \2", x)
    x = re.sub(r"\b0?(\d):", r"\1:", x)
    X = x.upper()
    for fmt in ("%I:%M %p", "%I %p"):
        try:
            dt = datetime.strptime(X, fmt)
            return dt.strftime("%-I:%M %p") if ":" in X else dt.strftime("%-I %p")
        except ValueError:
            continue
    return p.strip()

def _extract_times_from_segment(seg: str):
    s = re.sub(r"\s+to\s+", " - ", seg, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip()
    # full range
    m = re.search(r"(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)\s*[-–—]\s*(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)", s, re.I)
    if m:
        a, b = _fmt_one_time(m.group(1)), _fmt_one_time(m.group(2))
        # if AM→AM and b<=a, bump to PM
        try:
            sdt = datetime.strptime(a, "%-I:%M %p")
            edt = datetime.strptime(b, "%-I:%M %p")
            if "AM" in a and "AM" in b and edt <= sdt:
                edt = edt + timedelta(hours=12)
                b = edt.strftime("%-I:%M %p")
        except Exception:
            pass
        return f"{a} - {b}"
    # single time
    m = re.search(r"(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)", s, re.I)
    if m:
        return _fmt_one_time(m.group(1))
    return ""

def _normalize_time_for_upload(raw: str, library: str, year=None, month=None, day=None) -> str:
    t = (raw or "").strip()
    if not t:
        return ""

    cleaned = t  # default pass-through

    # --- Special parsing ONLY for VisitChesapeake (multi-day segments like "Tue–Fri ...; Sat–Sun ...") ---
    if library == "visitchesapeake":
        # Drop obvious labels at the very start
        t2 = re.sub(r"^\s*(?:time|times|hours|start|starts)\s*:\s*", "", t, flags=re.I)

        # Split into logical chunks by semicolons
        segs = [s for s in re.split(r"\s*;\s*", t2) if s.strip()]
        if not segs:
            cleaned = ""
        else:
            wkd = _wk_from_ymd(year, month, day)

            # Score each segment: does its dayset include today?
            scored = []
            for s in segs:
                days = _segment_dayset(s)
                has_time = bool(re.search(r"\d", s))
                score = 0
                if has_time: score += 1
                if wkd is not None and days and wkd in days: score += 2
                if wkd is not None and not days: score += 1  # no day mentioned → generic
                scored.append((score, s))

            # pick best segment
            best = max(scored, key=lambda x: x[0])[1]
            cleaned = _extract_times_from_segment(best)

            # Fallback: if nothing parsed from best, try others
            if not cleaned:
                for _, s in sorted(scored, reverse=True):
                    cleaned = _extract_times_from_segment(s)
                    if cleaned:
                        break

    # --- Treat 'start only' or 'start - 11:59 PM' as start+60 for selected libs ---
    if library in PLACEHOLDER_1159_FOR and cleaned:
        # normalize dashes/whitespace/nbsp
        cand = cleaned.replace("\u00A0", " ")
        cand = re.sub(r"\s*[–—]\s*", " - ", cand)
        cand = re.sub(r"\s+", " ", cand).strip()
    
        # Case A: single start time only
        if re.match(r"^\s*\d{1,2}(:\d{2})?\s*[AP]M\s*$", cand, re.I):
            start_norm = _fmt_one_time(cand)
            return _synthesize_one_hour_range(start_norm, year, month, day, minutes=60)
    
        # Case B: placeholder 11:59 end
        m = re.search(r"^\s*(\d{1,2}(?::\d{2})?\s*[ap]m)\s*-\s*(?:11:59\s*pm|23:59)\s*$", cand, re.I)
        if m:
            start_norm = _fmt_one_time(m.group(1))
            return _synthesize_one_hour_range(start_norm, year, month, day, minutes=60)
    
        cleaned = cand  # keep normalized spacing


    # --- Generic: if the result is a single time, synthesize +60 for selected libs ---
    if cleaned and library in SYNTHESIZE_SINGLE_FOR:
        if re.match(r"^\s*\d{1,2}(:\d{2})?\s*[AP]M\s*$", cleaned, re.I):
            start_norm = _fmt_one_time(cleaned)  # ensure 'H:MM AM/PM'
            return _synthesize_one_hour_range(start_norm, year, month, day, minutes=60)

    return cleaned


def _has_valid_time_str(t: str) -> bool:
    t = (t or "").strip().lower()
    if not t:
        return False
    # treat “All Day” style as valid
    if t in ("all day", "all-day", "all day event", "all-day event"):
        return True
    # accept anything that contains at least one AM/PM time
    return bool(TIME_OK.search(t))

def _clean_link(url: str) -> str:
    cleaned = (
        url.replace("/index.php/", "/")
           .replace("/index.php", "/")
    )
    return cleaned.replace("://", ":::").replace("//", "/").replace(":::", "://")


import os, json
from google.oauth2 import service_account

def connect_to_sheet(spreadsheet_name, worksheet_name):
    creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not creds_json:
        secret_path = "/etc/secrets/GOOGLE_APPLICATION_CREDENTIALS_JSON"
        if os.path.exists(secret_path):
            with open(secret_path, "r") as f:
                creds_json = f.read()
    if not creds_json:
        raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS_JSON env var not set")

    creds_dict = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    client = gspread.authorize(creds)

    # 👇 Master override
    if USE_MASTER_SHEET:
        if MASTER_SPREADSHEET_ID:
            return client.open_by_key(MASTER_SPREADSHEET_ID).worksheet(MASTER_WORKSHEET_NAME)
        return client.open(MASTER_SPREADSHEET_NAME).worksheet(MASTER_WORKSHEET_NAME)

    # per-library fallback
    return client.open(spreadsheet_name).worksheet(worksheet_name)

def connect_to_master_sheet(worksheet_name):
    creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not creds_json:
        secret_path = "/etc/secrets/GOOGLE_APPLICATION_CREDENTIALS_JSON"
        if os.path.exists(secret_path):
            with open(secret_path, "r") as f:
                creds_json = f.read()
    if not creds_json:
        raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS_JSON env var not set")

    creds_dict = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    client = gspread.authorize(creds)

    if MASTER_SPREADSHEET_ID:
        return client.open_by_key(MASTER_SPREADSHEET_ID).worksheet(worksheet_name)
    return client.open(MASTER_SPREADSHEET_NAME).worksheet(worksheet_name)


def normalize(row):
    return [cell.strip() for cell in row[:13]] + [""] * (13 - len(row))

def _kw_hit(text: str, kw: str) -> bool:
    t = (text or "").lower()
    k = (kw or "").lower()
    # match kw as a whole word/phrase (no letter/number touching it)
    return re.search(rf'(?<!\w){re.escape(k)}(?!\w)', t) is not None

# --- Units-aware age & grade parsing helpers ---

MONTH_WORDS = r"(?:months?|mos?|mths?|mo|m)"
YEAR_WORDS  = r"(?:years?|yrs?|y)"

def _grade_to_year_range(g: int):
    # crude but reliable mapping: K≈5-5.99 (we’ll treat 'K' separately), Grade N ≈ (N+5) to (N+5.99)
    start = g + 5
    return (start, start + 0.99)

def _extract_year_spans(text: str):
    """
    Returns a list of (min_years, max_years) tuples derived from months/years/grades in text.
    Months are converted to years. Also recognizes Pre-K/K/Grades and school level phrases.
    """
    t = (text or "").lower()
    spans = []

    # --- MONTHS FIRST (ranges, then singles) ---
    for m in re.finditer(rf"(\d{{1,2}})\s*(?:[-–]|to)\s*(\d{{1,2}})\s*{MONTH_WORDS}\b", t, flags=re.I):
        a, b = int(m.group(1))/12.0, int(m.group(2))/12.0
        spans.append((a, b))

    for m in re.finditer(rf"(\d{{1,2}})\s*{MONTH_WORDS}\b", t, flags=re.I):
        v = int(m.group(1))/12.0
        spans.append((v, v))

    # --- EXPLICIT YEARS ---
    # (1) year range like "3–5 years"
    for m in re.finditer(rf"(\d{{1,2}})\s*[-–]\s*(\d{{1,2}})\s*{YEAR_WORDS}\b", t, flags=re.I):
        a, b = int(m.group(1)), int(m.group(2))
        spans.append((a, b))

    # generic "ages: X[-–|to]Y" (or "ages X[-–|to]Y") WITHOUT months
    for m in re.finditer(
        rf"""
        ages?\s*[: ]*                           # allow optional colon after 'age/ages'
        (?!\d+\s*(?:[-–]|to)\s*\d+\s*{MONTH_WORDS}\b)   # not "ages 12–24 months" OR "ages 12 to 24 months"
        (?!\d+\s*{MONTH_WORDS}\b)                      # not "ages 12 months"
        (?!\d+\s*to\s*\d+\s*{MONTH_WORDS}\b)           # extra guard: not "ages 6 to 24 months"
        (\d{{1,2}})(?:\s*(?:[-–]|to)\s*(\d{{1,2}}))?
        \b
        """,
        t, flags=re.I | re.X
    ):
        a = int(m.group(1)); b = int(m.group(2) or a)
        spans.append((a, b))


    # (3) "X+ years" — also guard against "X+ months"
    for m in re.finditer(rf"(\d{{1,2}})\s*\+\s*(?:{YEAR_WORDS})?(?!\s*{MONTH_WORDS})\b", t, flags=re.I):
        a = int(m.group(1)); spans.append((a, 99))

    # (3b) "X and above / X and up / X and over / X or older" (treat like 'X+'), BUT not months
    for m in re.finditer(
        rf"""
        (?:age|ages|target\s*age)?\s*[: ]*
        (\d{{1,2}})
        (?!\s*{MONTH_WORDS}\b)                 # don't match "12 months and older"
        \s*(?:and\s+(?:above|over|up)|or\s+older)\b
        """,
        t, flags=re.I | re.X
    ):
        a = int(m.group(1))
        # Keep this clamp if you DON'T want 'Adults 18+' added for phrases like "16 and up".
        # If you do want Adults in those cases, change 17.99 to 99.
        hi = 17.99 if 12 <= a <= 17 else 99
        spans.append((a, hi))


    # --- GRADES & SCHOOL LEVELS ---
    if re.search(r"\b(pre[-\s]?k|prek|prekinder(?:garten)?)\b", t): spans.append((3.0, 4.99))
    if re.search(r"\bkindergarten\b|\bK\b", t, re.I): spans.append((5.0, 5.99))
    for m in re.finditer(r"grades?\s*(\d{1,2})(?:\s*[-–]\s*(\d{1,2}))?\b", t, flags=re.I):
        g1 = int(m.group(1)); g2 = int(m.group(2) or g1)
        a1, b1 = _grade_to_year_range(g1); a2, b2 = _grade_to_year_range(g2)
        spans.append((min(a1, a2), max(b1, b2)))
    if re.search(r"\belementary\b", t):      spans.append((5.0, 10.99))
    if re.search(r"\bmiddle\s+school\b", t): spans.append((11.0, 13.99))
    if re.search(r"\bhigh\s+school\b", t):   spans.append((14.0, 17.99))
    if re.search(r"\btween[s]?\b", t):       spans.append((9.0, 12.99))
    if re.search(r"\bteen[s]?\b", t):        spans.append((12.0, 17.99))

    return spans

def _spans_to_audience_tags(spans):
    """Map aggregated year spans into audience tags using our policy cutoffs."""
    if not spans:
        return []

    mn = min(a for a, _ in spans)
    mx = max(b for _, b in spans)

    tags = []
    # toddler/infant if any months present OR mx <= 2.5
    if mx <= 2.5:
        tags.append("Audience - Toddler/Infant")
        tags.append("Audience - Parent & Me")  # most sub-2.5y are caregiver events

    # preschool overlap
    if mx >= 3.0 and mn <= 4.99:
        tags.append("Audience - Preschool Age")

    # school-age overlap
    if mx >= 5.0 and mn <= 11.99:
        tags.append("Audience - School Age")

    # teens overlap
    if mx >= 13.0 and mn <= 17.99 and not (mx <= 2.5):
        tags.append("Audience - Teens")

    return list(dict.fromkeys(tags))


def upload_events_to_sheet(events, sheet=None, mode="full", library="vbpl", age_to_categories={}, name_suffix_map={}):
    library = (library or "").lower()
    config = get_library_config(library)

    # Default per-library destinations
    SPREADSHEET_NAME   = config["spreadsheet_name"]
    WORKSHEET_NAME     = config["worksheet_name"]
    LOG_WORKSHEET_NAME = config["log_worksheet_name"]

    # FORCE all uploads to Master
    if USE_MASTER_SHEET:
        SPREADSHEET_NAME = MASTER_SPREADSHEET_NAME
        WORKSHEET_NAME = MASTER_WORKSHEET_NAME
        LOG_WORKSHEET_NAME = MASTER_LOG_WORKSHEET_NAME

    library_constants = LIBRARY_CONSTANTS.get(library, {})
    program_type_to_categories = library_constants.get("program_type_to_categories", {})
    venue_names_map_lc = {k.lower(): v for k, v in library_constants.get("venue_names", {}).items()}
    age_to_categories = age_to_categories or library_constants.get("age_to_categories", {})
    name_suffix_map = name_suffix_map or library_constants.get("name_suffix_map", {})
    always_on = library_constants.get("always_on_categories", [])
    
    try:
        if sheet is None:
            sheet = connect_to_sheet(SPREADSHEET_NAME, WORKSHEET_NAME)

        rows = sheet.get_all_values()
        headers = rows[0]
        existing_rows = rows[1:]

        for i, row in enumerate(existing_rows):
            if len(row) < 16:
                print(f"[WARN] Row {i + 2} too short: {len(row)} cols → {row}")
                row += [""] * (16 - len(row))

        link_to_row_index = {}
        existing_data = {}

        for idx, row in enumerate(existing_rows):
            if len(row) <= 1:
                continue
            clean_link = _clean_link(row[1].strip())
            link_to_row_index[clean_link] = idx + 2
            existing_data[clean_link] = row

        # NEW: de-dupe guard for this run (sheet links + anything we queue below)
        seen_links = set(existing_data.keys())

        added = 0
        updated = 0
        skipped = 0

        new_rows = []
        update_requests = []

        
        for event in events:
            try:
                raw_link = (event.get("Event Link", "") or "").strip()
                if not raw_link:
                    print(f"⚠️  Skipping malformed event (missing link): {event.get('Event Name','')}")
                    skipped += 1
                    continue
        
                link = _clean_link(raw_link)

                # NEW: prevent duplicates within the same upload run (same Event Link)
                if link in seen_links:
                    print(f"⏭️ Skipping duplicate-in-run: {link}")
                    skipped += 1
                    continue
        
                title_for_filter = (event.get("Event Name", "") or "").strip()
                if _has_unwanted_title(title_for_filter):
                    print(f"⏭️ Skipping (unwanted title): {title_for_filter}")
                    skipped += 1
                    continue
        
                # === Exclude unwanted events for specific scrapers ===
                if library in ["visitsuffolk", "portsvaevents", "visitnewportnews", "visithampton", "visitchesapeake"]:
                    exclude_keywords = ["live", "patio"]
                    name_text = (event.get("Event Name", "") or "").lower()
                    desc_text = (event.get("Event Description", "") or "").lower()
                    if any(kw in name_text for kw in exclude_keywords) or any(kw in desc_text for kw in exclude_keywords):
                        print(f"⏭️ Skipping (excluded keyword): {event.get('Event Name')}")
                        skipped += 1
                        continue
        
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
                # 0) Start from what the scraper provided
                scraper_cats = [c.strip() for c in (event.get("Categories", "") or "").split(",") if c.strip()]
        
                # 1) Program-type based categories
                program_type = event.get("Program Type", "")
                title_for_filter = (event.get("Event Name") or "").strip()
        
                if library == "ppl":
                    programtype_cats = [c.strip() for c in (event.get("Categories", "") or "").split(",") if c.strip()]
                    if not programtype_cats:
                        programtype_cats = [c.strip() for c in "Audience - Family Event, Audience - Free Event, Audience - Preschool Age, Audience - School Age, Event Location - Portsmouth".split(",")]
                elif library == "hpl":
                    program_types = [pt.strip().lower() for pt in program_type.split(",") if pt.strip()]
                    matched_tags = []
                    for pt in program_types:
                        cat = program_type_to_categories.get(pt)
                        if cat:
                            safe_cat = _protect_special_labels(cat)
                            matched_tags.extend([_restore_special_labels(c.strip()) for c in safe_cat.split(",")])
                    programtype_cats = list(dict.fromkeys(matched_tags))
                else:
                    base_pt = program_type_to_categories.get(program_type, "")
                    programtype_cats = [c.strip() for c in base_pt.split(",") if c.strip()]
        
                # 2) Age-based categories (mapped + fuzzy)
                ages_raw = event.get("Ages", "") or ""
                audience_keys = [a.strip() for a in ages_raw.split(",") if a.strip()]
        
                mapped_age_tags = []
                if age_to_categories:
                    for tag in audience_keys:
                        tags = age_to_categories.get(tag)
                        if tags:
                            mapped_age_tags.extend([t.strip() for t in tags.split(",")])
        
                desc_value = (
                    event.get("Event Description")
                    or event.get("Description")
                    or event.get("Desc")
                    or event.get("Event Details")
                    or ""
                )
                title_text = (event.get("Event Name", "") or "")
                age_haystack = f"{title_text} {desc_value} {ages_raw}"
                # normalize fancy dashes/hyphens so K–5/K—5/K-5 all behave like K-5
                age_haystack = (
                    age_haystack
                    .replace("\u2011", "-")  # non-breaking hyphen
                    .replace("\u2012", "-")
                    .replace("\u2013", "-")  # en dash
                    .replace("\u2014", "-")  # em dash
                )
                is_school_age_phrase  = re.search(r"\bschool age\b", age_haystack, re.I)
                mentions_elementary   = re.search(r"\belementary\b", age_haystack, re.I)
                
                # Elementary → School Age (accept K/kindergarten and 1–5, with "-" or "to")
                mentions_grades_elm = re.search(
                    r"\bgrades?\s*(k|kindergarten|[1-5])(st|nd|rd|th)?(?:\s*(?:-|to)\s*(k|kindergarten|[1-5])(st|nd|rd|th)?)?\b",
                    age_haystack,
                    re.I
                )
            
                mentions_high_school   = re.search(r"\bhigh\s+school\b", age_haystack, re.I)
                mentions_middle_school = re.search(r"\bmiddle\s+school\b", age_haystack, re.I)
                age_tags = _spans_to_audience_tags(_extract_year_spans(age_haystack))
        
                def _has_audience_tag(tags):
                    return any((t or "").startswith("Audience -") for t in tags)
        
                age_combined = list(mapped_age_tags)
                if age_tags and not _has_audience_tag(mapped_age_tags):
                    age_combined.extend(age_tags)
        
                # 3) Keyword tags (single + paired)
                full_text = f"{event.get('Event Name', '')} {desc_value}".lower()
                title_text_l = (event.get("Event Name", "") or "").lower()
        
                title_based_tags = []
                for keyword, cat in TITLE_KEYWORD_TO_CATEGORY.items():
                    if _kw_hit(title_text_l, keyword) or _kw_hit(full_text, keyword):
                        safe_cat = _protect_special_labels(cat)
                        title_based_tags.extend([_restore_special_labels(c.strip()) for c in safe_cat.split(",")])
        
                for (kw1, kw2), cat in COMBINED_KEYWORD_TO_CATEGORY.items():
                    if _kw_hit(full_text, kw1) and _kw_hit(full_text, kw2):
                        safe_cat = _protect_special_labels(cat)
                        title_based_tags.extend([_restore_special_labels(c.strip()) for c in safe_cat.split(",")])
        
                # 4) Always-on tags for this library
                tag_list = []
                tag_list.extend(scraper_cats)
                tag_list.extend(programtype_cats)
                tag_list.extend(age_combined)
                tag_list.extend(title_based_tags)
                if always_on:
                    tag_list.extend(always_on)

                # ✅ add the School Age tag based on grades K–5 detection
                if (is_school_age_phrase or mentions_elementary or mentions_grades_elm) and not (mentions_high_school or mentions_middle_school):
                    _ensure(tag_list, "Audience - School Age")
    
                # --- YPL: always add base tags ---
                if library == "ypl":
                    _ensure(tag_list, "Audience - Free Event")
                    _ensure(tag_list, "Event Location - Yorktown / York County")

                # 5) Fallback if nothing at all
                if not tag_list:
                    raw_location = (event.get("Location", "") or "").strip()
                    fallback_city = ""
                    for city in ("Norfolk", "Virginia Beach", "Chesapeake", "Portsmouth", "Hampton", "Newport News", "Suffolk"):
                        if city.lower() in raw_location.lower():
                            fallback_city = city
                            break
                    tag_list.append(
                        f"Event Location - {fallback_city}, Audience - Free Event"
                        if fallback_city else "Audience - Free Event"
                    )
        
                # VBPL debug (optional)
                if library == "vbpl":
                    title_l = (event.get("Event Name","") or "").lower()
                    hay_l   = f"{title_l} {(desc_value or '').lower()} {(ages_raw or '').lower()}"
                    if "baby" in title_l or "months" in hay_l:
                        print("DBG VBPL:", event.get("Event Name"),
                              "| spans:", _extract_year_spans(hay_l),
                              "| age_tags:", age_tags,
                              "| program_type:", program_type,
                              "| title_kw_hits:", [k for k in TITLE_KEYWORD_TO_CATEGORY if _kw_hit(title_l, k) or _kw_hit(hay_l, k)])
                        
                # Remove preschool tag for "Just 2s / Just 2's" titles
                tag_list = _strip_preschool_for_just2s(event.get("Event Name", ""), tag_list)

                # Remove incorrect Storytimes when VBPL titles say "Open Play"
                if library == "vbpl":
                    tag_list = _strip_storytime_for_open_play(event.get("Event Name", ""), tag_list)

                # Remove Halloween tags from November/December events
                month_val = event.get("Month", "")
                tag_list = _strip_halloween_from_late_events(month_val, tag_list)

                # Remove school-age tag for "3s Please" titles
                tag_list = _strip_schoolage_for_3splease(event.get("Event Name", ""), tag_list)

                # Final clean & dedupe
                categories = ", ".join(dict.fromkeys([t.replace("\u00A0", " ").replace("Â", "").strip() for t in tag_list if t.strip()]))

                # --- Hampton (VisitHampton) custom rule: mark library events as free ---
                if library == "visithampton":
                    venue = (event.get("Venue", "") or "").lower()
                    location = (event.get("Location", "") or "").lower()
                    if "library" in venue or "library" in location:
                        if "Audience - Free Event" not in categories:
                            categories += ", Audience - Free Event"
                            print(f"🏷️ Added Free Event tag (library venue) → {event.get('Event Name')}")

                # === Normalize title and (maybe) suffix ===
                name_original = event.get("Event Name", "")
                name_without_at = re.sub(r"\s*@\s*[^@,;:\\/]+", "", name_original, flags=re.IGNORECASE).strip()
                if library == "visithampton":
                    name_cleaned = name_without_at
                else:
                    name_cleaned = re.sub(r"\s+at\s+.*", "", name_without_at, flags=re.IGNORECASE).strip()
        
                if library == "visithampton":
                    pref_loc = (event.get("Venue", "") or "").strip() or (event.get("Location", "") or "").strip()
                else:
                    pref_loc = (event.get("Location", "") or "").strip()
        
                suffix = config.get("event_name_suffix", "")
                loc_clean = re.sub(r"^Library Branch:", "", pref_loc).strip()
                display_loc = name_suffix_map.get(loc_clean, loc_clean)
        
                base_name = name_cleaned.lower()
                loc_lower = display_loc.lower()
                suffix_lower = (suffix or "").lower()
        
                if base_name.endswith(loc_lower) or suffix_lower in base_name:
                    event_name = f"{name_cleaned}"
                else:
                    event_name = f"{name_cleaned} at {display_loc}"
                if suffix and suffix not in event_name:
                    event_name += suffix
        
                if not categories:
                    categories = event.get("Categories", "") or f"Event Location - {config['organizer_name']}, Audience - Free Event, Audience - Family Event"
        
                # Decide sheet location (Column F)
                organizer = (event.get("Organizer", "") or "").strip().lower()
                if library == "visithampton" and organizer == "fort monroe national monument":
                    raw_location = "Fort Monroe Visitor & Education Center"
                elif library == "visithampton":
                    raw_location = (event.get("Venue", "") or "").strip()
                else:
                    raw_location = (event.get("Location", "") or "").strip()
        
                if library == "visitchesapeake":
                    raw_location = _strip_room_suffix(raw_location)
        
                loc_key = re.sub(r"^Library Branch:", "", raw_location).strip()
                venue_map_present = bool(venue_names_map_lc)
                venue_in_map      = venue_map_present and (loc_key.lower() in venue_names_map_lc)
                sheet_location    = venue_names_map_lc.get(loc_key.lower(), loc_key)
        
                time_str = _normalize_time_for_upload(
                    event.get("Time", ""),
                    library,
                    event.get("Year"), event.get("Month"), event.get("Day")
                )
        
                row_core = [
                    event_name,
                    link,
                    event.get("Event Status", ""),
                    time_str,
                    event.get("Ages", ""),
                    sheet_location,
                    event.get("Month", ""),
                    event.get("Day", ""),
                    event.get("Year", ""),
                    desc_value,
                    event.get("Series", ""),
                    program_type,
                    categories
                ]
                print("🧾 Raw row_core before normalize:", row_core)
                new_core = normalize(row_core)
        
                existing_row  = existing_data.get(link, [""] * 16)
                existing_core = normalize(existing_row)
        
                # --- Needs-Attention logic ---
                t = (time_str or "").strip().lower()
                title = (event.get("Event Name") or "")
        
                enforce_venue_map     = (library in ENFORCE_VENUE_MAP_FOR)
                missing_mapped_venue  = enforce_venue_map and venue_map_present and (not venue_in_map)
        
                is_all_day     = ("all day" in t) or ("ongoing" in t)
                start_present  = bool(re.search(r"\b\d{1,2}(:\d{2})?\s*[ap]m\b", t, re.I))
                has_end        = bool(re.search(r"\b\d{1,2}(:\d{2})?\s*[ap]m\b\s*[-–—]\s*\d{1,2}(:\d{2})?\s*[ap]m\b", t, re.I))
                missing_end_time = (not is_all_day) and start_present and (not has_end)
        
                missing_desc  = not (desc_value or "").strip()
                missing_loc   = not (sheet_location or "").strip()
                invalid_time  = not _has_valid_time_str(time_str)
                is_exhibit    = "exhibit" in title.lower()
        
                needs_attention = any([
                    missing_desc,
                    missing_loc,
                    invalid_time,
                    is_exhibit,
                    missing_mapped_venue,
                    missing_end_time
                ])
        
                # --- Row status/state machine ---
                if needs_attention:
                    site_sync_status = "NEEDS ATTENTION"
                    status = "review needed"
                else:
                    status = "new"
                    site_sync_status = existing_row[15] if link in existing_data else "new"
        
                if link in existing_data:
                    existing_vals = {
                        "status": existing_row[2],
                        "month": existing_row[6],
                        "day":   existing_row[7],
                        "year":  existing_row[8],
                        "time":  existing_row[3],
                    }
                    current_vals = {
                        "status": event.get("Event Status", ""),
                        "month":  event.get("Month", ""),
                        "day":    event.get("Day", ""),
                        "year":   event.get("Year", ""),
                        "time":   event.get("Time", "")
                    }
                    changed_to_cancelled = (
                        existing_vals["status"].lower() != current_vals["status"].lower()
                        and current_vals["status"].lower() == "cancelled"
                    )
                    date_changed = (
                        existing_vals["month"] != current_vals["month"]
                        or existing_vals["day"] != current_vals["day"]
                        or existing_vals["year"] != current_vals["year"]
                    )
                    time_changed = existing_vals["time"] != current_vals["time"]
                    if changed_to_cancelled or date_changed or time_changed:
                        status = "updates needed"
                        if site_sync_status == "on site":
                            site_sync_status = "updates needed"
                    else:
                        status = existing_row[14]
                        site_sync_status = site_sync_status or ""
        
                full_row = new_core + [now, status, site_sync_status]
        
                if link not in existing_data:
                    print("🔍 New row to append:", full_row)
                    new_rows.append(full_row)
                    seen_links.add(link)   
                    added += 1
                elif new_core != existing_core:
                    print(f"🔄 Updated row {link_to_row_index[link]}:", full_row)
                    row_index = link_to_row_index[link]
                    update_requests.append({
                        "range": f"A{row_index}:P{row_index}",
                        "values": [full_row]
                    })
                    updated += 1
        
            except Exception as e:
                print(f"💥 Error processing event '{event.get('Event Name','')}' ({event.get('Event Link','')}): {e}")
                # traceback.print_exc()  # uncomment if you want full stack
                error_count += 1
                continue


        if update_requests:
            sheet.batch_update(update_requests)

        # Export REVIEW NEEDED rows to CSV
        review_rows = [r for r in new_rows if "REVIEW NEEDED" in r[-1]]
#       if review_rows:
#           review_df = pd.DataFrame(review_rows, columns=headers[:len(review_rows[0])])
#           review_path = f"Review Needed - Missing Info - {library}.csv"
#           review_df.to_csv(review_path, index=False)
#           print(f"📎 Exported {len(review_rows)} flagged rows to {review_path}")
#
#            send_notification_email_with_attachment(
#            review_path,
#            f"{library.upper()} — Review Needed: Missing Info",
#            config["email_recipient"]
#           )

        if new_rows:
            # Optional: comment this out if it's too chatty
            # print("🔍 Full row to upload:", full_row)
            sheet.append_rows(new_rows, value_input_option="USER_ENTERED")
        
        try:
            log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_row = [log_time, mode, added, updated, (skipped + error_count)]
        
            if USE_MASTER_SHEET:
                log_sheet = connect_to_master_sheet(LOG_WORKSHEET_NAME)
            else:
                log_sheet = connect_to_sheet(SPREADSHEET_NAME, LOG_WORKSHEET_NAME)
        
            log_sheet.append_row(log_row, value_input_option="USER_ENTERED")
            print(f"🪵 Logged summary to {LOG_WORKSHEET_NAME}: {log_row}")
        except Exception as e:
            print(f"⚠️ Failed to log to {LOG_WORKSHEET_NAME} tab: {e}")

        
        print(f"📦 {added} new events added.")
        print(f"🔁 {updated} existing events updated.")
        if skipped:
            print(f"🧹 {skipped} malformed events skipped.")

    except Exception as e:
        print(f"❌ upload_events_to_sheet failed for library='{library}': {e}")
        traceback.print_exc()
        # optional: re-raise if you want the caller/cron to fail loudly
        # raise


def export_all_events_to_csv_and_email():
    LIBRARIES = [
        "vbpl",
        "npl",
        "chpl",
        "nnpl",
        "hpl",
        "spl",
        "ppl",
        "visithampton",
        "visitchesapeake",
        "visitnewportnews",
        "portsvaevents",
        "visitsuffolk",
        "langleylibrary"
    ]
    all_rows = []
    for lib in LIBRARIES:
        print(f"📥 Fetching events from: {lib.upper()}")
        config = get_library_config(lib)
        creds = service_account.Credentials.from_service_account_file(
            "/etc/secrets/GOOGLE_APPLICATION_CREDENTIALS_JSON",
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        client = gspread.authorize(creds)
        sheet = client.open(config["spreadsheet_name"]).worksheet(config["worksheet_name"])
        rows = sheet.get_all_values()
        if not all_rows:
            all_rows.append(rows[0])  # headers once
        all_rows.extend(rows[1:])     # all events

    # Write to CSV
    df = pd.DataFrame(all_rows[1:], columns=all_rows[0])
    export_path = "All_Libraries_Events.csv"
    df.to_csv(export_path, index=False)
    print(f"✅ Exported {len(df)} rows to {export_path}")

    # Email it
    from export_to_csv import send_notification_email_with_attachment
    send_notification_email_with_attachment(
        export_path,
        "All Libraries – Events Export",
        os.environ.get("EVENT_EXPORT_RECIPIENT") or "your@email.com"
    )

if __name__ == "__main__":
    export_all_events_to_csv_and_email()


