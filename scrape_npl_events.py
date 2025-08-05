import requests
from datetime import datetime, timedelta
from time import sleep
from bs4 import BeautifulSoup
import re
from constants import UNWANTED_TITLE_KEYWORDS

def scrape_npl_events(mode="all"):
    print("🌐 Scraping Norfolk Public Library events via weekly date chunks...")

    events = []
    today = datetime.today()

    # Set the base start date
    if mode == "weekly":
        start_date = today
        end_date = today + timedelta(days=7)
    elif mode == "monthly":
        start_date = today
        end_date = start_date + timedelta(days=30)

    else:
        # Default to pulling a wide range (1st of current month to 1st of next-next month)
        start_date = today.replace(day=1)
        end_date = start_date + timedelta(days=60)

    current = start_date
    while current <= end_date:
        chunk_date = current.strftime("%Y-%m-%d")
        print(f"📆 Fetching chunk for date={chunk_date}")
        url = f"https://norfolk.libcal.com/ajax/calendar/list?c=-1&date={chunk_date}&perpage=100&page=1&audience=&cats=&camps=&inc=0"

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])

            for result in results:
                try:
                    title = result.get("title", "").strip()
                    title_lc = re.sub(r"[^\w\s]", "", title.lower())  # Remove punctuation
                    if any(kw in title_lc for kw in UNWANTED_TITLE_KEYWORDS):
                        print(f"⏭️ Skipping: Unwanted title match → {title}")
                        continue

                    dt = datetime.strptime(result["startdt"], "%Y-%m-%d %H:%M:%S")
                    end_dt = datetime.strptime(result["enddt"], "%Y-%m-%d %H:%M:%S")

                    audiences = result.get("audiences", [])
                    if len(audiences) == 1 and audiences[0].get("name", "").strip() == "Adults (18+)":
                        continue

                    ages = ", ".join([a.get("name", "") for a in audiences if "name" in a])

                    # Fallback: infer Adults 18+ from breadcrumb
                    if not ages.strip():
                        try:
                            detail_url = result.get("url", "")
                            detail_resp = requests.get(detail_url, timeout=10)
                            detail_soup = BeautifulSoup(detail_resp.text, "html.parser")
                            breadcrumb_links = detail_soup.select("nav[aria-label='breadcrumb'] a")
                            for link in breadcrumb_links:
                                if "Adult Programs" in link.get_text():
                                    ages = "Adults 18+"
                                    break
                            if not ages.strip():
                                tag_links = detail_soup.select("a[href*='/calendar?cid=']")
                                for tag in tag_links:
                                    if "Adult Programs" in tag.get_text():
                                        ages = "Adults 18+"
                                        break
                        except Exception as e:
                            print(f"⚠️ Failed to fetch breadcrumb for {title}: {e}")

                    start = result.get("start", "").strip()
                    end = result.get("end", "").strip()
                    if result.get("all_day", False):
                        time_str = "All Day Event"
                    elif start and end:
                        time_str = f"{start} – {end}"
                    elif start:
                        time_str = start
                    else:
                        time_str = ""

                    location = result.get("campus", "").strip() or result.get("location", "").strip()

                    if not location:
                        match = re.search(r"@ ([\w\- ]+)", title)
                        if match:
                            short_name = match.group(1).strip()
                            name_map = {
                                "Tucker": "Richard A. Tucker Memorial Library",
                                "Pretlow": "Mary D. Pretlow Anchor Branch Library",
                                "Barron F. Black": "Barron F. Black Branch Library",
                                "Jordan-Newby": "Jordan-Newby Anchor Branch Library at Broad Creek",
                                "Blyden": "Blyden Branch Library",
                                "Lafayette": "Lafayette Branch Library",
                                "Larchmont": "Larchmont Branch Library",
                                "Van Wyck": "Van Wyck Branch Library",
                                "Downtown": "Downtown Branch at Slover",
                                "Park Place": "Park Place Branch Library",
                                "Little Creek": "Little Creek Branch Library",
                                "Janaf": "Janaf Branch Library"
                            }
                            for key, full_name in name_map.items():
                                if short_name.lower() in key.lower():
                                    location = full_name
                                    break
                    # === Category tagging logic ===

                    text_to_match = f"{title} {result.get('description', '')}".lower()
                    
                    # 1. Match keyword categories
                    keyword_tags = []
                    for keyword, tag_string in TITLE_KEYWORD_TO_CATEGORY.items():
                        if keyword.lower() in text_to_match:
                            keyword_tags.extend([t.strip() for t in tag_string.split(",")])
                    
                    # 2. Add base location + free tag
                    base_location_tag = "Event Location - Norfolk"
                    free_tag = "Audience - Free Event"  # You can always add this for NPL unless charging logic is found
                    
                    # 3. Age tags via map_age_to_categories
                    min_age = 0
                    max_age = 0
                    ages_lc = ages.lower()
                    if "teen" in ages_lc:
                        min_age, max_age = 13, 17
                    elif "school" in ages_lc or "grade" in ages_lc:
                        min_age, max_age = 5, 12
                    elif "preschool" in ages_lc:
                        min_age, max_age = 3, 5
                    elif "infant" in ages_lc or "baby" in ages_lc:
                        max_age = 2
                    
                    age_tags = []
                    if min_age or max_age:
                        age_tags = [tag.strip() for tag in map_age_to_categories(min_age, max_age).split(",") if tag.strip()]
                    
                    # 4. Merge and deduplicate
                    final_categories = sorted(set([base_location_tag, free_tag] + keyword_tags + age_tags))
                    categories = ", ".join(final_categories)

                    
                    events.append({
                        "Event Name": title,
                        "Event Link": result.get("url", ""),
                        "Event Status": "Available",
                        "Time": time_str,
                        "Categories": categories,
                        "Ages": ages,
                        "Location": location,
                        "Month": dt.strftime("%b"),
                        "Day": str(dt.day),
                        "Year": str(dt.year),
                        "Event Date": dt.strftime("%Y-%m-%d"),
                        "Event End Date": end_dt.strftime("%Y-%m-%d"),
                        "Event Description": result.get("description", "").strip(),
                        "Series": "",
                        "Program Type": "",
                    })
                except Exception as e:
                    print(f"⚠️ Error parsing event: {e}")

        except Exception as err:
            print(f"❌ Failed to fetch page for {chunk_date}: {err}")

        current += timedelta(days=7)
        sleep(0.5)

    print(f"✅ Scraped {len(events)} events total.")
    return events
