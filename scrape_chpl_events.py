import requests
from datetime import datetime, timedelta
import json
from bs4 import BeautifulSoup
from constants import UNWANTED_TITLE_KEYWORDS, TITLE_KEYWORD_TO_CATEGORY, LIBRARY_CONSTANTS
from calendar import monthrange

def _end_of_next_month(dt):
    y = dt.year + (1 if dt.month == 12 else 0)
    m = 1 if dt.month == 12 else dt.month + 1
    last = monthrange(y, m)[1]
    # 23:59:59 so an all-day event on the last day is included
    return datetime(y, m, last, 23, 59, 59)


def _get_full_desc_from_chpl_detail(url, headers):
    """
    Return the long, real description from CHPL event pages.
    - Only reads AMH text blocks that contain <p>/<li> (not headers/branch/location)
    - Skips any block that contains H1–H4, branch anchors, or looks like a menu
    - No meta-description fallback (to avoid nav text)
    """
    try:
        r = requests.get(url, headers=headers, timeout=12)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Hard remove obvious non-content areas
        for sel in [
            "nav", "header", "footer", "aside",
            ".breadcrumb", ".breadcrumbs", ".site-nav", ".menu",
            ".sr-only", ".visually-hidden", "[aria-hidden='true']",
            ".skip-links", ".skiplink", ".offcanvas", "#global-nav"
        ]:
            for n in soup.select(sel):
                n.decompose()

        root = soup.select_one("main, #main, #main-content, .l-main, .page-content, .region-content") or soup

        # Very specific: AMH text blocks that actually have P/LI and NO headers or branch links
        blocks = root.select(
            '.amh-block.amh-text[data-block-type="text"]:has(p), '
            '.amh-block.amh-text[data-block-type="text"]:has(ul li)'
        )

        candidates = []
        nav_vocab = {"home", "about us", "library", "online resources", "how do i", "catalog"}

        for b in blocks:
            # Skip if this block contains any headers (H1–H4) or branch/location anchors
            if b.select("h1, h2, h3, h4, a[href^='#branch'], a[href*='branch']"):
                continue

            # Collect paragraph/list text only
            parts = [t.get_text(" ", strip=True) for t in b.select("p, li") if t.get_text(strip=True)]
            if not parts:
                continue

            txt = "\n\n".join(parts).strip()

            # Drop very short blobs
            if len(txt) < 40:
                continue

            tlow = txt.lower()

            # Heuristic: nav-ish if it contains multiple menu words OR almost no punctuation
            punct = tlow.count(".") + tlow.count("!") + tlow.count("?")
            hits = sum(1 for w in nav_vocab if w in tlow)
            if hits >= 2 or (punct == 0 and len(txt) < 200):
                continue

            candidates.append(txt)

        # Choose the longest remaining block (most complete description)
        return max(candidates, key=len).strip() if candidates else ""
    except Exception:
        return ""


def scrape_chpl_events(mode="all"):
    print("✨ Scraping Chesapeake Public Library events...")

    today = datetime.today()
    base_url = "https://events.chesapeakelibrary.org/eeventcaldata"

    start_date = today

    if mode == "weekly":
        end_date = today + timedelta(days=7)
    elif mode == "monthly":
        end_date = _end_of_next_month(today)     # 👈 end of the following month
    else:
        end_date = today + timedelta(days=90)
    
    days = (end_date - start_date).days + 1  # inclusive span


    payload = {
        "private": False,
        "date": today.strftime("%Y-%m-%d"),
        "days": days,
        "locations": [],
        "ages": [],
        "types": []
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest"
    }

    response = requests.get(
        base_url,
        params={"event_type": 0, "req": json.dumps(payload)},
        headers=headers,
        timeout=20
    )
    response.raise_for_status()
    data = response.json()

    events = []

    for item in data:
        try:
            dt = datetime.strptime(item["event_start"], "%Y-%m-%d %H:%M:%S")
            
            # ⛔ absolute guardrail so over-delivered series don’t leak through
            if not (start_date <= dt <= end_date):
                continue
                
            if mode == "weekly" and dt > today + timedelta(days=7):
                continue

            # Time logic
            time_str = item.get("time_string", "")
            if time_str.lower() in ("all day", "all day event"):
                time_str = "All Day Event"

            ages = item.get("ages", "")

            title = item.get("title", "").strip()

            # 🚫 Skip unwanted titles
            if any(bad_word in title.lower() for bad_word in UNWANTED_TITLE_KEYWORDS):
                print(f"⏭️ Skipping: Unwanted title match → {title}")
                continue
            
            event_url = item.get("url", "").replace("\\/", "/")
            status = "Available"
            
            # ✅ Check for cancellation
            if item.get("changed") == "1":
                try:
                    detail_resp = requests.get(event_url, headers=headers, timeout=10)
                    detail_soup = BeautifulSoup(detail_resp.text, "html.parser")
                    cancelled_msg = detail_soup.select_one(".eelist-changed-message")
                    if cancelled_msg and "cancelled" in cancelled_msg.get_text(strip=True).lower():
                        status = "Cancelled"
                except Exception as e:
                    print(f"⚠️ Failed to fetch detail page for status check: {event_url} — {e}")
            
            # ✅ Category tagging from title + ages
            title_lower = title.lower()
            keyword_tags = [tag for keyword, tag in TITLE_KEYWORD_TO_CATEGORY.items() if keyword in title_lower]
            
            program_type_to_categories = LIBRARY_CONSTANTS["chpl"].get("program_type_to_categories", {})
            age_to_categories = LIBRARY_CONSTANTS["chpl"].get("age_to_categories", {})
            audience_keys = [a.strip() for a in ages.split(",") if a.strip()]
            age_tags = []
            for key in audience_keys:
                tags = age_to_categories.get(key)
                if tags:
                    age_tags.extend([t.strip() for t in tags.split(",")])
            
            all_categories = ", ".join(dict.fromkeys(keyword_tags + age_tags))  # dedupe while preserving order

            api_desc = (item.get("description", "") or "").strip()
            event_url = (item.get("url", "") or "").replace("\\/", "/")
            
            # If the API blurb looks short, fetch the full body from the detail page
            full_desc = api_desc
            if not api_desc or len(api_desc) < 140 or ("\n" not in api_desc and api_desc.count(".") <= 1):
                long_txt = _get_full_desc_from_chpl_detail(event_url, headers)
                if long_txt and len(long_txt) > len(api_desc):
                    full_desc = long_txt

            # ✅ Final event append
            events.append({
                "Event Name": title,
                "Event Link": event_url,
                "Event Status": status,
                "Time": time_str,
                "Ages": ages,
                "Location": item.get("location", "").strip(),
                "Month": dt.strftime("%b"),
                "Day": str(dt.day),
                "Year": str(dt.year),
                "Event Date": dt.strftime("%Y-%m-%d"),
                "Event Description": full_desc,
                "Series": "Yes" if item.get("recurring_id") else "",
                "Program Type": item.get("tags", ""),
                "Categories": all_categories
            })
            
        except Exception as e:
            print(f"⚠️ Error processing event: {e}")
        
    print(f"✅ Scraped {len(events)} events from Chesapeake.")
    return events
