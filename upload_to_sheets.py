
import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re

# --- CONFIG ---
SPREADSHEET_NAME = "Virginia Beach Library Events"
WORKSHEET_NAME = "VBPL Events"
SHEET_HEADERS = ["Event Name", "Event Link", "Event Status", "Time", "Ages", "Location", "Month", "Day", "Year", "Event Description"]

def remove_emojis(text):
    return re.sub(r"[^\w\s.,;:!?&@()\"'/-]", "", text)

def connect_to_sheet(spreadsheet_name, worksheet_title):
    json_creds_str = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not json_creds_str:
        raise RuntimeError("Missing GOOGLE_SERVICE_ACCOUNT_JSON environment variable")

    creds_dict = json.loads(json_creds_str)
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    client = gspread.authorize(creds)

    spreadsheet = client.open(spreadsheet_name)
    return spreadsheet.worksheet(worksheet_title)

def get_existing_event_links(sheet):
    try:
        records = sheet.get_all_records()
        return set(row["Event Link"] for row in records if "Event Link" in row)
    except Exception as e:
        print(f"⚠️ Failed to fetch existing records: {e}")
        return set()

def fetch_event_data():
    url = "https://vbpl.librarymarket.com/events/month"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    events = []
    cards = soup.select("article.event-card")
    print(f"🔍 Found {len(cards)} event cards.")

    for card in cards:
        try:
            link_tag = card.select_one("a.lc-event__link")
            if not link_tag:
                continue
            name = link_tag.text.strip()
            link = "https://vbpl.librarymarket.com" + link_tag.get("href", "")
            status = card.select_one(".lc-registration-label")
            time = card.select_one(".lc-event-info-item--time")
            ages = card.select_one(".lc-event-info__item--colors")
            location = card.select_one(".lc-event__branch")

            # Detail fields
            detail_response = requests.get(link)
            detail_soup = BeautifulSoup(detail_response.content, "html.parser")
            description_tag = detail_soup.select_one(".field--name-body .field-item")
            description = description_tag.text.strip() if description_tag else ""

            month = detail_soup.select_one(".lc-date-icon__item--month")
            day = detail_soup.select_one(".lc-date-icon__item--day")
            year = detail_soup.select_one(".lc-date-icon__item--year")

            record = {
                "Event Name": remove_emojis(name),
                "Event Link": link,
                "Event Status": remove_emojis(status.text.strip() if status else ""),
                "Time": remove_emojis(time.text.strip() if time else ""),
                "Ages": remove_emojis(ages.text.strip() if ages else ""),
                "Location": remove_emojis(location.text.strip() if location else ""),
                "Month": month.text.strip() if month else "",
                "Day": day.text.strip() if day else "",
                "Year": year.text.strip() if year else "",
                "Event Description": remove_emojis(description)
            }

            events.append(record)
        except Exception as e:
            print(f"⚠️ Error parsing card: {e}")

    return events

def upload_events_to_sheet(events, sheet):
    existing_links = get_existing_event_links(sheet)
    new_rows = [list(event.values()) for event in events if event["Event Link"] not in existing_links]
    print(f"📦 {len(new_rows)} new events to upload.")

    if new_rows:
        sheet.append_rows(new_rows, value_input_option="USER_ENTERED")
    else:
        print("✅ No new events found to upload.")

def main():
    print("🚀 Starting scrape...")
    events = fetch_event_data()
    sheet = connect_to_sheet(SPREADSHEET_NAME, WORKSHEET_NAME)
    upload_events_to_sheet(events, sheet)
    print("✅ Done uploading.")

if __name__ == "__main__":
    main()
