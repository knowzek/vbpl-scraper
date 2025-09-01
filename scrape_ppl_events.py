# scrape_ppl_events.py
from datetime import datetime, timedelta, timezone
import re
import requests
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo
from urllib.parse import urljoin, quote

from constants import (
    LIBRARY_CONSTANTS,
    TITLE_KEYWORD_TO_CATEGORY,
    UNWANTED_TITLE_KEYWORDS,
)

# -------------------------
# Config
# -------------------------
eastern = ZoneInfo("America/New_York")
BASE = "https://www.portsmouthpubliclibrary.org"

# Pull from BOTH calendars
CIDS = ["24", "23"]
# Try combined first (both orders), then singles
CID_VARIANTS = ["24,23", "23,24", "24", "23"]

SESSION = requests.Session()
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.8",
}

# -------------------------
# Helpers
# -------------------------

def is_likely_adult_event(text: str) -> bool:
    t = (text or "").lower()
    keywords = [
        "adult", "18+", "21+", "resume", "job help", "tax help",
        "medicare", "investment", "retirement", "social security",
        "veterans", "finance", "knitting", "real estate"
    ]
    return any(kw in t for kw in keywords)

def _fetch_print_description(eid: str) -> str:
    """
    CivicPlus print detail page often contains the clean description even
    when the standard detail template is sparse/protected.
    """
    print_url = f"{BASE}/Common/Components/Calendar/Event-Details-Print.aspx?EID={eid}"
    try:
        headers = dict(HEADERS)
        headers["Referer"] = f"{BASE}/calendar.aspx"
        resp = SESSION.get(print_url, headers=headers, timeout=30)
        if resp.status_code >= 400:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        for selector in [
            "#EventDescription", ".cp-event-description", ".Description",
            ".eventDetailDescription", ".itemDescription"
        ]:
            el = soup.select_one(selector)
            if el:
                txt = el.get_text(" ", strip=True)
                if len(txt) >= 5:
                    return txt
        body = soup.find("body")
        return body.get_text(" ", strip=True) if body else ""
    except Exception:
        return ""


def extract_ages(text: str) -> str:
    """Lightweight age bucket extraction."""
    text = (text or "").lower()
    matches = set()

    # Range detection: ages 4–11, ages 5 – 12
    range_match = re.search(r"ages?\s*(\d{1,2})\s*[-–to]+\s*(\d{1,2})", text)
    if range_match:
        low = int(range_match.group(1))
        high = int(range_match.group(2))
        if high <= 3:
            matches.add("Infant")
        elif high <= 5:
            matches.add("Preschool")
        elif high <= 12:
            matches.add("School Age")
        elif high <= 17:
            matches.add("Teens")
        else:
            matches.add("Adults 18+")

    under_match = re.search(r"(under|younger than)\s*(\d{1,2})", text)
    if under_match:
        age = int(under_match.group(2))
        if age <= 3:
            matches.add("Infant")
        elif age <= 5:
            matches.add("Preschool")
        else:
            matches.add("School Age")

    if any(kw in text for kw in ["infants", "babies", "baby", "0-2"]):
        matches.add("Infant")
    if any(kw in text for kw in ["toddlers", "2-3", "2 and 3", "age 2", "age 3", "preschool"]):
        matches.add("Preschool")
    if any(kw in text for kw in ["school age", "elementary", "5-8", "ages 5", "grade"]):
        matches.add("School Age")
    if any(kw in text for kw in ["tween", "tweens", "middle school"]):
        matches.add("Tweens")
    if any(kw in text for kw in ["teen", "teens", "high school"]):
        matches.add("Teens")
    if "all ages" in text:
        matches.add("All Ages")

    return ", ".join(sorted(matches))

def is_cancelled(name: str, description: str) -> bool:
    t1 = (name or "").lower()
    t2 = (description or "").lower()
    return ("cancelled" in t1) or ("canceled" in t1) or ("cancelled" in t2) or ("canceled" in t2)

def _candidate_month_urls(cid: str, year: int, month: int) -> list[str]:
    """
    Try several CivicPlus variants for a given CID string (e.g., "24", "23", "24,23").
    """
    m = str(month)
    y = str(year)
    cid_encoded = quote(cid)  # encodes the comma if present (24%2C23)
    return [
        # Reliable for many sites: base category page (usually current month)
        f"{BASE}/calendar.aspx?CID={cid}",
        f"{BASE}/calendar.aspx?CID={cid_encoded}",
        # Explicit month/year variants:
        f"{BASE}/calendar.aspx?CID={cid}&curm={m}&cury={y}",
        f"{BASE}/calendar.aspx?CID={cid_encoded}&curm={m}&cury={y}",
        f"{BASE}/calendar.aspx?CID={cid}&month={m}&year={y}",
        f"{BASE}/calendar.aspx?CID={cid_encoded}&month={m}&year={y}",
        # Date-form param used by some configs:
        f"{BASE}/calendar.aspx?CID={cid}&startDate={m}%2F1%2F{y}",
        f"{BASE}/calendar.aspx?CID={cid_encoded}&startDate={m}%2F1%2F{y}",
    ]

def _fetch_month_event_links(year: int, month: int) -> list[str]:
    """
    Union of ?EID= links across combined + individual CIDs.
    """
    links = set()
    for cid in CID_VARIANTS:
        for url in _candidate_month_urls(cid, year, month):
            try:
                headers = dict(HEADERS)
                headers["Referer"] = f"{BASE}/calendar.aspx"
                resp = SESSION.get(url, headers=headers, timeout=30)
                if resp.status_code >= 400:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if "calendar.aspx?eid=" in href.lower():
                        links.add(urljoin(BASE, href))
            except Exception:
                continue
    return sorted(links)

def _parse_time12(t: str):
    t = (t or "").upper().replace(".", "").strip()
    for fmt in ("%I:%M %p", "%I %p"):
        try:
            return datetime.strptime(t, fmt)
        except ValueError:
            continue
    return None

def _fmt_time12(dt: datetime | None) -> str:
    if not dt:
        return ""
    return dt.strftime("%-I:%M %p")

def _parse_event_detail(url: str) -> dict:
    """
    Parse a CivicPlus event detail page and extract title, description,
    location, date, and times. Tolerant to template differences / redirects.
    """
    headers = dict(HEADERS)
    headers["Referer"] = f"{BASE}/calendar.aspx"

    try:
        resp = SESSION.get(url, headers=headers, timeout=30, allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # init for date/description so we can safely set them early
        date_obj = None
        description = ""
    except Exception:
        return {}

    # Title (avoid generic "Calendar")
    title = ""
    for sel in ["#lblEventName", ".itemTitle", "h1#lblEventName", "h1", "h2"]:
        el = soup.select_one(sel)
        if el:
            title = el.get_text(strip=True)
            break
    if (not title) or (title.strip().lower() == "calendar"):
        meta = soup.find("meta", attrs={"property": "og:title"})
        if meta and meta.get("content"):
            t2 = meta["content"].strip()
            if t2 and t2.lower() != "calendar":
                title = t2

    # B1) CivicPlus date+description container first
    desc_div = soup.select_one(".detailDateDesc")
    if desc_div:
        # try to grab the date header inside the block, e.g. <h3 id="...eventDate">
        h = desc_div.find(["h3", "h2", "h4"], id=re.compile("eventDate", re.IGNORECASE))
        if not h:  # fallback: first heading in the block
            h = desc_div.find(["h3", "h2", "h4"])
        if h:
            date_txt = h.get_text(" ", strip=True)
            mdate = re.search(r"([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})", date_txt)
            if mdate and not date_obj:
                try:
                    date_obj = datetime.strptime(
                        f"{mdate.group(1)} {mdate.group(2)} {mdate.group(3)}",
                        "%B %d %Y"
                    ).replace(tzinfo=eastern)
                except Exception:
                    pass
            h.extract()  # remove the date header so only the narrative remains
    
        # whatever text remains is the description
        cand = desc_div.get_text(" ", strip=True)
        if len(cand) >= 5:
            description = cand


    # Description (only from likely event containers)
    if not description:
        for selector in [
            "#EventDescription", ".eventDetailDescription", ".cp-event-description",
            ".Description", "#EventBody", ".itemDescription", ".event_desc",
        ]:
            el = soup.select_one(selector)
            if el:
                description = el.get_text(" ", strip=True)
                if len(description) >= 5:
                    break
    
    # Meta description fallback
    if not description:
        meta = soup.find("meta", attrs={"property": "og:description"}) \
            or soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            mtxt = meta["content"].strip()
            if len(mtxt) >= 5:
                description = mtxt
    
    # Print-page fallback (grab clean text even if the detail template is sparse)
    if not description:
        m_eid = re.search(r"[?&]EID=(\d+)", url, re.IGNORECASE)
        if m_eid:
            description = _fetch_print_description(m_eid.group(1))


    # Location via labeled block
    location = ""
    for row in soup.select("dl, .cp-details, .detail_list"):
        text = row.get_text(" ", strip=True)
        m = re.search(r"Location\s*:?\s*(.+)", text, re.IGNORECASE)
        if m:
            loc = m.group(1)
            loc = re.split(r"\b(Date|Time|Cost|Contact|Phone|Email)\b\s*:?", loc, 1, flags=re.IGNORECASE)[0]
            location = loc.strip()
            break

    # Date from page text, else URL fallbacks (only if not already set)
    full_text = soup.get_text(" ", strip=True)
    
    if not date_obj:
        mdate = re.search(
            r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})",
            full_text, re.IGNORECASE
        )
        if mdate:
            month_name = mdate.group(2)
            day = int(mdate.group(3))
            year = int(mdate.group(4))
            try:
                date_obj = datetime.strptime(f"{month_name} {day} {year}", "%B %d %Y").replace(tzinfo=eastern)
            except Exception:
                date_obj = None
    
    if not date_obj:
        m1 = re.search(r"(EventDate|date)=(\d{1,2})/(\d{1,2})/(\d{4})", url, re.IGNORECASE)
        if m1:
            mon = int(m1.group(2)); day = int(m1.group(3)); year = int(m1.group(4))
            try:
                date_obj = datetime(year, mon, day, tzinfo=eastern)
            except Exception:
                pass
    
    if not date_obj:
        m2 = re.search(r"[?&]month=(\d{1,2}).*?[&]day=(\d{1,2}).*?[&]year=(\d{4})", url, re.IGNORECASE)
        if m2:
            mon = int(m2.group(1)); day = int(m2.group(2)); year = int(m2.group(3))
            try:
                date_obj = datetime(year, mon, day, tzinfo=eastern)
            except Exception:
                pass

    # Time range (range or single)
    start_time = end_time = ""
    mt = re.search(r"(\d{1,2}:\d{2}\s*[AP]M)\s*[-–—]\s*(\d{1,2}:\d{2}\s*[AP]M)", full_text, re.IGNORECASE)
    if mt:
        start_time = _fmt_time12(_parse_time12(mt.group(1)))
        end_time   = _fmt_time12(_parse_time12(mt.group(2)))
    else:
        one = re.search(r"(?:Time\s*:?\s*|at\s+)(\d{1,2}:\d{2}\s*[AP]M)", full_text, re.IGNORECASE)
        if one:
            start_time = _fmt_time12(_parse_time12(one.group(1)))

    return {
        "title": title,
        "description": description,
        "location": location,
        "date_obj": date_obj,
        "start_time": start_time,
        "end_time": end_time,
    }

def _dedupe_keep_order(items):
    seen, out = set(), []
    for x in items:
        if x and x not in seen:
            out.append(x); seen.add(x)
    return out

# -------------------------
# Main scrape
# -------------------------

def scrape_ppl_events(mode="all"):
    print("📚 Scraping Portsmouth Public Library (HTML month iterator, CIDs: 24 & 23)…")

    today = datetime.now(timezone.utc).astimezone(eastern).replace(hour=0, minute=0, second=0, microsecond=0)
    if mode == "weekly":
        end_cutoff = today + timedelta(days=7)
    elif mode == "monthly":
        end_cutoff = today + timedelta(days=30)
    else:
        end_cutoff = today + timedelta(days=90)

    # months to fetch: current + next
    this_year, this_month = today.year, today.month
    next_dt = today + timedelta(days=32)
    next_year, next_month = next_dt.year, next_dt.month

    month_links = []
    for (y, m) in [(this_year, this_month), (next_year, next_month)]:
        links = _fetch_month_event_links(y, m)
        print(f"🗓 Found {len(links)} event links for {y}-{m:02d}")
        month_links.extend(links)

    detail_links = _dedupe_keep_order(month_links)

    ppl_constants = LIBRARY_CONSTANTS.get("ppl", {})
    venue_map = ppl_constants.get("venue_names", {}) or {}
    age_to_categories = ppl_constants.get("age_to_categories", {}) or {}

    DEFAULT_CATEGORIES = (
        "Audience - Family Event, Audience - Free Event, "
        "Audience - Preschool Age, Audience - School Age, Event Location - Portsmouth"
    )

    events = []
    for link in detail_links:
        try:
            data = _parse_event_detail(link)
            if not data:
                continue

            name = (data.get("title") or "").strip()
            description = (data.get("description") or "").strip()
            raw_location = (data.get("location") or "").strip()
            event_date_obj = data.get("date_obj")

            if not event_date_obj:
                print(f"⚠️ No date on detail; skipping: {link}")
                continue

            # Date window: today → end_cutoff
            if event_date_obj < today or event_date_obj > end_cutoff:
                continue

            # Skip unwanted titles
            if any(bad_word in name.lower() for bad_word in UNWANTED_TITLE_KEYWORDS):
                print(f"⏭️ Skipping (unwanted title): {name}")
                continue

            # Adult filter AFTER we know it's a real event
            if is_likely_adult_event(name) or is_likely_adult_event(description):
                print(f"⏭️ Skipping (adult): {name}")
                continue

            # Normalize location via map
            location = venue_map.get(raw_location, raw_location) or "Portsmouth Main Library"

            start_time = data.get("start_time") or ""
            end_time   = data.get("end_time") or ""
            time_str = f"{start_time} - {end_time}" if (start_time and end_time) else (start_time or "")

            ages = extract_ages(name + " " + description)

            # Title keyword tags
            base_cats = []
            combined_text = (name + " " + description).lower()
            for keyword, cat in TITLE_KEYWORD_TO_CATEGORY.items():
                if keyword in combined_text:
                    base_cats.extend([c.strip() for c in cat.split(",")])

            # Age mapping tags
            age_tags = []
            for a in [a.strip() for a in (ages or "").split(",") if a.strip()]:
                cat = age_to_categories.get(a)
                if cat:
                    age_tags.extend([c.strip() for c in cat.split(",")])

            # Always add these for PPL
            all_tags = [c.strip() for c in base_cats + age_tags if c.strip()]
            all_tags.extend(["Audience - Free Event", "Event Location - Portsmouth"])
            categories = ", ".join(dict.fromkeys(all_tags)) or DEFAULT_CATEGORIES

            events.append({
                "Event Name": name or "Library Event",
                "Event Link": link,
                "Event Status": "Cancelled" if is_cancelled(name, description) else "Available",
                "Time": time_str,
                "Ages": ages,
                "Location": location,
                "Month": event_date_obj.strftime("%b"),
                "Day": str(event_date_obj.day),
                "Year": str(event_date_obj.year),
                "Event Date": event_date_obj.strftime("%Y-%m-%d"),
                "Event End Date": event_date_obj.strftime("%Y-%m-%d"),
                "Event Description": description,
                "Series": "",
                "Program Type": "",
                "Categories": categories
            })

        except Exception as e:
            print(f"⚠️ Error parsing detail: {link} → {e}")

    print(f"✅ Scraped {len(events)} events from PPL (HTML, multi-CID).")
    return events
