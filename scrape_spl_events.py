import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re

BASE_URL = "https://suffolkpubliclibrary.libcal.com/calendar?cid=-1&t=d&d=0000-00-00&cal=-1&inc=0"


def is_likely_adult_event(text):
    text = text.lower()
    keywords = [
        "adult", "18+", "21+", "job help", "resume", "medicare",
        "investment", "retirement", "social security", "veterans",
        "seniors", "tax help", "real estate", "finance", "knitting"
    ]
    return any(kw in text for kw in keywords)


def extract_ages(text):
    text = text.lower()
    matches = set()

    if any(kw in text for kw in ["infants", "babies", "baby", "birth to 2", "0-2"]):
        matches.add("Infant")
    if any(kw in text for kw in ["toddlers", "2-3", "2 and 3", "age 2", "age 3"]):
        matches.add("Preschool")
    if any(kw in text for kw in ["preschool", "ages 3-5", "3-5"]):
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


def scrape_spl_events(mode="all"):
    print("🗭 Scraping Suffolk Public Library events...")

    today = datetime.now()

    if mode == "weekly":
        start_date = today
        end_date = today + timedelta(days=7)
    elif mode == "monthly":
        start_date = today
        if today.month == 12:
            next_month = datetime(today.year + 1, 1, 1)
        else:
            next_month = datetime(today.year, today.month + 1, 1)
        if next_month.month == 12:
            following_month = datetime(next_month.year + 1, 1, 1)
        else:
            following_month = datetime(next_month.year, next_month.month + 1, 1)
        end_date = following_month - timedelta(days=1)
    else:
        start_date = today
        end_date = today + timedelta(days=90)

    events = []
    page = 1

    while True:
        print(f"🔄 Fetching page {page}...")
        resp = requests.get(BASE_URL, params={
            "cid": "-1",
            "t": "d",
            "d": "0000-00-00",
            "cal": "-1",
            "inc": "0",
            "page": str(page)
        })

        soup = BeautifulSoup(resp.text, "html.parser")
        event_listings = soup.find_all("div", class_="media s-lc-c-evt")
        if not event_listings:
            print("⚠️ No event listings found on page")
            break

        for listing in event_listings:
            try:
                title_tag = listing.find("h3", class_="media-heading")
                name = title_tag.get_text(strip=True) if title_tag else "Untitled Event"
                url_tag = title_tag.find("a") if title_tag else None
                url = url_tag["href"] if url_tag and url_tag.has_attr("href") else ""

                desc_tag = listing.find("div", class_="s-lc-c-evt-des")
                desc = desc_tag.get_text(strip=True) if desc_tag else ""

                info = {}
                dl = listing.find("dl", class_="dl-horizontal")
                if dl:
                    for dt_tag in dl.find_all("dt"):
                        key = dt_tag.get_text(strip=True).rstrip(":").lower()
                        dd_tag = dt_tag.find_next_sibling("dd")
                        if dd_tag:
                            info[key] = dd_tag.get_text(strip=True)

                date_text = info.get("date", "")
                try:
                    dt = datetime.strptime(date_text, "%A, %B %d, %Y")
                    end_dt = dt
                except:
                    print("⚠️ Could not parse date:", date_text)
                    continue

                time_str = info.get("time", "")
                location = info.get("location", "Suffolk Public Library")

                if is_likely_adult_event(name) or is_likely_adult_event(desc):
                    continue

                ages = extract_ages(name + " " + desc)

                events.append({
                    "Event Name": name,
                    "Event Link": url,
                    "Event Status": "Available",
                    "Time": time_str,
                    "Ages": ages,
                    "Location": location,
                    "Month": dt.strftime("%b"),
                    "Day": str(dt.day),
                    "Year": str(dt.year),
                    "Event Date": dt.strftime("%Y-%m-%d"),
                    "Event End Date": end_dt.strftime("%Y-%m-%d"),
                    "Event Description": desc,
                    "Series": "",
                    "Program Type": "",
                    "Categories": ""
                })

            except Exception as e:
                print(f"⚠️ Error processing event: {e}")

        page += 1

    print(f"✅ Scraped {len(events)} events from SPL.")
    return events
