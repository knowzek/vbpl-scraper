import gspread
from oauth2client.service_account import ServiceAccountCredentials
import asyncio
from scrape_vbpl import scrape  # Make sure scrape_vbpl.py returns a list of dicts
import os
import json

# Load JSON from environment variable
SERVICE_ACCOUNT_INFO = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_INFO, [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
])
client = gspread.authorize(creds)


# Connect to Google Sheets
def connect_to_sheet(sheet_name):
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
    client = gspread.authorize(creds)
    return client.open(sheet_name).sheet1

def get_existing_links(sheet):
    links = sheet.col_values(2)[1:]  # Assuming column 2 = Event Link, skip header
    return set(links)

def append_new_events(sheet, new_events, existing_links):
    for event in new_events:
        if event["Event Link"] not in existing_links:
            row = [
                event["Event Name"],
                event["Event Link"],
                event["Event Status"],
                event["Time"],
                event["Ages"],
                event["Location"],
                event["Month"],
                event["Day"],
                event["Year"],
                event["Event Description"]
            ]
            sheet.append_row(row, value_input_option="USER_ENTERED")

async def main():
    print("🚀 Starting scrape...")
    new_events = await scrape()
    print(f"📦 {len(new_events)} events scraped.")

    sheet = connect_to_sheet("VBPL Events")
    existing_links = get_existing_links(sheet)
    print(f"📄 {len(existing_links)} existing links in sheet.")

    append_new_events(sheet, new_events, existing_links)
    print("✅ Done uploading.")

if __name__ == "__main__":
    asyncio.run(main())
