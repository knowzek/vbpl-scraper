import requests
from datetime import datetime, timedelta
import json
from bs4 import BeautifulSoup
from constants import UNWANTED_TITLE_KEYWORDS, TITLE_KEYWORD_TO_CATEGORY, LIBRARY_CONSTANTS

def _get_full_desc_from_chpl_detail(url, headers):
    """
    Fetch a long, cleaned description from a CHPL event detail page.
    - Targets only AMH text blocks that contain real <p> text
    - Skips blocks that are just headers, locations, or dates
    """
    try:
        r = requests.get(url, headers=headers, timeout=12)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        candidates = []

        # Only look inside AMH blocks that actually have <p> with text
        for node in soup.select(".amh-block.amh-text .amh-content"):
            parts = [t.get_text(" ", strip=True) for t in node.select("p, li") if t.get_text(strip=True)]
            if not parts:
                continue

            txt = "\n\n".join(parts).strip()

            # --- Filter out junk blocks (dates, location headers, etc.) ---
            if any(x in txt.lower() for x in [
                "central library", "major hillard library", "greenbrier library",
                "russell memorial library", "indian river library",
                "south norfolk memorial library", "cuffee library",
                "wednesday", "thursday", "friday", "monday", "tuesday", "saturday", "sunday"
            ]):
                continue

            if len(txt) < 40:  # very short = likely not a real description
                continue

            candidates.append(txt)

        # Fall back to meta description if nothing
        if not candidates:
            meta = soup.find("meta", attrs={"name": "description"})
            if meta and meta.get("content"):
                return meta["content"].strip()

        return max(candidates, key=len).strip() if candidates else ""
    except Exception:
        return ""

def scrape_chpl_events(mode="all"):
    print("✨ Scraping Chesapeake Public Library events...")

    today = datetime.today()
    base_url = "https://events.chesapeakelibrary.org/eeventcaldata"

    if mode == "weekly":
        days = 7
    elif mode == "monthly":
        days = 30
    else:
        days = 90  # Default fetch 90 days if no filter

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
                    detail_resp = requests.get(event_url, timeout=10)
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
