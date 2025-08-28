import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import re
from constants import LIBRARY_CONSTANTS, TITLE_KEYWORD_TO_CATEGORY, COMBINED_KEYWORD_TO_CATEGORY, UNWANTED_TITLE_KEYWORDS


base_url = "https://poquoson.librarycalendar.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}
MAX_PAGES = 50

def _dedupe_keep_order(items):
    seen, out = set(), []
    for x in items:
        if x and x not in seen:
            out.append(x); seen.add(x)
    return out

def _kw_hit(text: str, kw: str) -> bool:
    t = (text or "").lower()
    k = (kw or "").lower()
    return re.search(rf'(?<!\w){re.escape(k)}(?!\w)', t) is not None

# Map LibraryCalendar “Age Group” text → audience tags
def _age_groups_to_tags(ages_text: str, organizer="Poquoson"):
    t = (ages_text or "").lower()
    tags = []
    # coarse buckets
    if any(w in t for w in ["baby", "babies", "infant", "0-2"]):
        tags += ["Audience - Toddler/Infant"]
    if any(w in t for w in ["toddler", "preschool", "pre-k", "ages 3", "ages 4", "3-5"]):
        tags += ["Audience - Preschool Age", "Audience - Parent & Me"]
    if any(w in t for w in ["kids", "children", "school age", "elementary", "grades"]):
        tags += ["Audience - School Age"]
    if any(w in t for w in ["tween", "tweens", "middle school"]):
        tags += ["Audience - School Age"]
    if any(w in t for w in ["teen", "teens", "high school", "young adult"]):
        tags += ["Audience - Teens"]
    if "all ages" in t or "family" in t:
        tags += ["Audience - Free Event"]  # keep “free” as a default audience tag
    # Always include location tag
    tags += [f"Event Location - {organizer}"]
    return _dedupe_keep_order(tags)

# Program Type → default tags (VBPL-style), fallback to constants override if present
def _program_type_to_tags(program_type: str, organizer="Poquoson"):
    base = {
        "Storytimes & Early Learning": f"Event Location - {organizer}, Audience - Free Event, Audience - Family Event, List - Storytimes",
        "STEAM": f"Event Location - {organizer}, List - STEM/STEAM, Audience - Free Event, Audience - Family Event",
        "Computers & Technology": f"Event Location - {organizer}, Audience - Free Event, Audience - Teens, Audience - Family Event",
        "Workshops & Lectures": f"Event Location - {organizer}, Audience - Free Event, Audience - Family Event",
        "Discussion Groups": f"Event Location - {organizer}, Audience - Free Event, Audience - Family Event",
        "Arts & Crafts": f"Event Location - {organizer}, Audience - Free Event, Audience - Family Event",
        "Hobbies": f"Event Location - {organizer}, Audience - Free Event, Audience - Family Event",
        "Books & Authors": f"Event Location - {organizer}, Audience - Free Event, Audience - Family Event",
        "Culture": f"Event Location - {organizer}, Audience - Free Event, Audience - Family Event",
        "History & Genealogy": f"Event Location - {organizer}, Audience - Teens, Audience - Free Event",
    }
    # constants override if provided
    from_constants = (LIBRARY_CONSTANTS.get("poquosonpl", {}) or {}).get("program_type_to_categories")
    mapping = {k.lower(): v for k, v in (from_constants or base).items()}
    tags = []
    for pt in [x.strip().lower() for x in (program_type or "").split(",") if x.strip()]:
        if pt in mapping:
            tags += [c.strip() for c in mapping[pt].split(",")]
    return _dedupe_keep_order(tags)

def _keyword_tags(title: str, description: str):
    txt_title = (title or "").lower()
    txt_full  = f"{title} {description}".lower()
    tags = []
    for kw, cats in TITLE_KEYWORD_TO_CATEGORY.items():
        if _kw_hit(txt_title, kw) or _kw_hit(txt_full, kw):
            tags += [c.strip() for c in cats.split(",")]
    for (kw1, kw2), cats in COMBINED_KEYWORD_TO_CATEGORY.items():
        if _kw_hit(txt_full, kw1) and _kw_hit(txt_full, kw2):
            tags += [c.strip() for c in cats.split(",")]
    return _dedupe_keep_order(tags)

def _build_categories(title, description, program_type, ages_text):
    organizer = "Poquoson"
    always_on = (LIBRARY_CONSTANTS.get("poquosonpl", {}) or {}).get("always_on_categories", [])
    age_map   = (LIBRARY_CONSTANTS.get("poquosonpl", {}) or {}).get("age_to_categories", {})
    tags = []

    # Program type tags
    tags += _program_type_to_tags(program_type, organizer=organizer)

    # Age tags: prefer explicit map (if ages_text already says Infant/Preschool/etc.), else coarse groups
    if age_map and ages_text:
        for token in [a.strip() for a in ages_text.split(",") if a.strip()]:
            mapped = age_map.get(token)
            if mapped:
                tags += [c.strip() for c in mapped.split(",")]
    if ages_text:
        tags += _age_groups_to_tags(ages_text, organizer=organizer)

    # Keyword tags (title + description)
    tags += _keyword_tags(title, description)

    # Always-on (e.g., Event Location - Poquoson, Audience - Family Event)
    tags += always_on

    # Final dedupe
    return ", ".join(_dedupe_keep_order(tags))


def extract_description(soup):
    """
    Robustly extract description from LibraryCalendar (LibraryMarket) pages.
    Handles both `.field--name-description` and `.field--name-body`,
    preserves basic line breaks and bullet lists.
    """
    # Try the usual suspects, in order
    sel = (
        ".field--name-description .field-item, "
        ".field--name-description, "
        ".field--name-body .field-item, "
        ".field--name-body, "
        ".event-body"
    )
    node = soup.select_one(sel)

    # Last-resort: meta description
    if not node:
        meta = soup.select_one('meta[name="description"]')
        return (meta["content"].strip() if meta and meta.get("content") else "")

    # Normalize HTML → text
    # 1) <br> → newline
    for br in node.find_all("br"):
        br.replace_with("\n")
    # 2) bullet lists → "- item" lines
    for li in node.find_all("li"):
        li.insert_before("\n- ")
    # Ensure paragraphs create spacing
    for p in node.find_all("p"):
        if p.text and not p.text.endswith("\n"):
            p.append("\n\n")

    text = node.get_text(separator="\n", strip=True)

    # Collapse excessive newlines
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text

def _abs(base: str, href: str) -> str:
    if not href:
        return base
    href = href.strip()
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return base + href
    return base + "/" + href



def scrape_poquosonpl_events(cutoff_date=None, mode="all"):
    
    events = []
    today = datetime.today()

    # allow main.py to pass cutoff_date; otherwise compute from mode
    if cutoff_date is None:
        if mode == "weekly":
            cutoff_date = today + timedelta(days=7)
        elif mode == "monthly":
            cutoff_date = today + timedelta(days=30)
        else:
            cutoff_date = today + timedelta(days=90)

    page = 0

    while page < MAX_PAGES:
        print(f"🌐 Fetching page {page}...")
        url = f"{base_url}/events/upcoming?page={page}"
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.select("article.lc-event-card, article.event-card, article.node--type-event")
        if not cards:
            print("✅ No more event cards found. Done scraping.")
            break

        for card in cards:
            try:
                link_tag = card.select_one("a.lc-event__link")
                name = link_tag.get_text(strip=True)
                link = _abs(base_url, link_tag["href"])
                # 🚫 Skip unwanted titles
                if any(bad_word in name.lower() for bad_word in UNWANTED_TITLE_KEYWORDS):
                    print(f"⏭️ Skipping: Unwanted title match → {name}")
                    continue
                print(f"🔗 Processing: {name} ({link})")

                # Extract event date from the card
                month_tag = card.select_one(".lc-date-icon__item--month")
                day_tag = card.select_one(".lc-date-icon__item--day")
                year_tag = card.select_one(".lc-date-icon__item--year")

                month_text = month_tag.get_text(strip=True) if month_tag else ""
                day_text = day_tag.get_text(strip=True) if day_tag else ""
                year_text = year_tag.get_text(strip=True) if year_tag else ""

                if not (month_text and day_text and year_text):
                    print(f"⚠️ Missing date parts for '{name}' — skipping")
                    continue

                try:
                    event_date = datetime.strptime(f"{month_text} {day_text} {year_text}", "%b %d %Y")
                except Exception as e:
                    print(f"⚠️ Failed to parse date for '{name}': {e}")
                    continue

                print(f"📅 Parsed date for '{name}': {event_date.date()}")

                if cutoff_date and event_date > cutoff_date:
                    print(f"🛑 '{name}' is beyond cutoff ({cutoff_date.date()}). Stopping pagination.")
                    return events

                # Extract summary info from card
                time_tag = card.select_one(".lc-event-info-item--time")
                time_slot = time_tag.get_text(strip=True) if time_tag else ""

                ages_tag = card.select_one(".lc-event-info__item--colors")
                ages = ages_tag.get_text(strip=True) if ages_tag else ""

                status_tag = card.select_one(".lc-registration-label")
                status = status_tag.get_text(strip=True) if status_tag else "Available"

                location_tag = card.select_one(".lc-event__branch")
                location = location_tag.get_text(strip=True) if location_tag else ""

                # Extract description
                # detail page
                time.sleep(0.4)
                d_resp = requests.get(link, headers=HEADERS, timeout=20)
                d_resp.raise_for_status()
                d_soup = BeautifulSoup(d_resp.text, "html.parser")
                
                # ✅ robust description extraction
                description = extract_description(d_soup)

                # Extract Program Type (used for category assignment)
                program_type_tag = d_soup.select_one(".lc-event__program-types span")
                series_block = d_soup.select_one(".lc-repeating-dates__details")
                
                # Detect if part of a series
                series_block = detail_soup.select_one(".lc-repeating-dates__details")
                is_series = "Yes" if series_block else ""

                categories = _build_categories(name, description, program_type, ages)
                # Append event to list
                events.append({
                    "Event Name": name,
                    "Event Link": link,
                    "Event Status": status,
                    "Time": time_slot,
                    "Ages": ages,
                    "Location": location,
                    "Month": month_text,
                    "Day": day_text,
                    "Year": year_text,
                    "Event Date": event_date.strftime("%Y-%m-%d"),
                    "Event Description": description,
                    "Series": is_series,
                    "Program Type": program_type,
                    "Categories": categories
                })

            except Exception as e:
                print(f"⚠️ Error parsing event: {e}")

        page += 1

    print(f"✅ Scraped {len(events)} total events.")
    return events
