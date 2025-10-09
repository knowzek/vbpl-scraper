import requests
from datetime import datetime, timedelta
import json
from bs4 import BeautifulSoup
from constants import UNWANTED_TITLE_KEYWORDS, TITLE_KEYWORD_TO_CATEGORY, LIBRARY_CONSTANTS
from calendar import monthrange
import re

EMOJI_RX = re.compile(
    "["                      # strip emoji (optional)
    "\U0001F000-\U0001FFFF"
    "\U00020000-\U0002FFFF"
    "\U00030000-\U0003FFFF"
    "]+", flags=re.UNICODE
)

def _clean_text(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = EMOJI_RX.sub("", s)                 # remove emojis
    s = s.replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _fetch_full_description(url: str, timeout: int = 15) -> str:
    """
    Open the event detail page and join all text from .amh-block.amh-text sections.
    """
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        parts = []
        # each text block
        for blk in soup.select(".amh-block.amh-text .amh-content"):
            # collect paragraphs (including lone <p> in nested spans)
            for p in blk.select("p"):
                t = p.get_text(" ", strip=True)
                if t:
                    parts.append(t)

        # fallback: sometimes the site uses <div> text without <p>
        if not parts:
            for blk in soup.select(".amh-block.amh-text"):
                t = blk.get_text(" ", strip=True)
                if t:
                    parts.append(t)

        desc = " ".join(parts)
        return _clean_text(desc)
    except Exception:
        return ""


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

            # --- Build merged description first (your block above) ---
            api_desc   = (item.get("description", "") or "").strip()
            detail_desc = _get_full_desc_from_chpl_detail(event_url, headers) or ""
            
            def _clean(s: str) -> str:
                s = re.sub(r"<[^>]+>", " ", s or "")
                s = s.replace("\xa0", " ")
                s = re.sub(r"\s+", " ", s).strip()
                return s
            
            api_desc    = _clean(api_desc)
            detail_desc = _clean(detail_desc)
            
            AGE_RX = re.compile(r"\bages?\b|\byears?\b|\bmonths?\b|\bcaregiver\b|\b0\s*[–-]\s*3\b", re.I)
            def _merge_desc(a: str, b: str) -> str:
                if not a: return b
                if not b: return a
                if a in b: return b
                if AGE_RX.search(b) and not AGE_RX.search(a):
                    return b if b.startswith(a[:120]) else f"{a.rstrip(' .')} {b}"
                if AGE_RX.search(a) and not AGE_RX.search(b):
                    return a
                return b if len(b) > len(a) and not b.startswith(a[:120]) else (a if len(a) >= len(b) else b)
            
            full_desc = _merge_desc(api_desc, detail_desc)
            
            # --- Category tagging (now that full_desc is ready) ---
            title_lower = (title or "").lower()
            desc_lower  = full_desc.lower()
            ages_str    = ages or ""
            
            def _kw_hit(text: str, kw: str) -> bool:
                # word-boundary hit to avoid 'steam' in 'upstream'
                return re.search(rf'(?<!\w){re.escape((kw or "").lower())}(?!\w)', (text or "").lower()) is not None
            
            program_type_to_categories = LIBRARY_CONSTANTS["chpl"].get("program_type_to_categories", {})
            age_to_categories         = LIBRARY_CONSTANTS["chpl"].get("age_to_categories", {})
            always_on                 = LIBRARY_CONSTANTS["chpl"].get("always_on_categories", [])
            
            # 1) Keyword tags (title OR description), expand multi-tag strings
            keyword_tags = []
            for keyword, tag_str in TITLE_KEYWORD_TO_CATEGORY.items():
                if _kw_hit(title_lower, keyword) or _kw_hit(desc_lower, keyword):
                    keyword_tags.extend([t.strip() for t in tag_str.split(",") if t.strip()])
            
            # 2) Program type → categories (CHPL puts types in item['tags'])
            pt_raw = (item.get("tags", "") or "").strip()
            pt_tags = []
            if pt_raw:
                mapped = program_type_to_categories.get(pt_raw) or ""
                pt_tags.extend([t.strip() for t in mapped.split(",") if t.strip()])
            
            # 3) Ages → categories (from the Ages field)
            audience_keys = [a.strip() for a in ages_str.split(",") if a.strip()]
            age_tags = []
            for key in audience_keys:
                tag_str = age_to_categories.get(key) or ""
                if tag_str:
                    age_tags.extend([t.strip() for t in tag_str.split(",") if t.strip()])
            
            # 4) Always-on tags for CHPL
            base_tags = list(always_on) if always_on else []
            
            # 5) Final categories (preserve order, dedupe)
            all_tags = base_tags + pt_tags + age_tags + keyword_tags
            all_categories = ", ".join(dict.fromkeys(all_tags))



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
