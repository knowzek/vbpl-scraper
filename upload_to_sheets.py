import gspread
from oauth2client.service_account import ServiceAccountCredentials
import asyncio
from scrape_vbpl import scrape  # Make sure scrape_vbpl.py returns a list of dicts

# Load credentials JSON
SERVICE_ACCOUNT_FILE = 'vbpl-scraper-2e2895e33305.json'  # Update filename if needed

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
    new_events = await scrape()
    sheet = connect_to_sheet("VBPL Events")  # Update with your actual sheet name
    existing_links = get_existing_links(sheet)
    append_new_events(sheet, new_events, existing_links)
    print(f"✅ Uploaded {len(new_events)} events (skipped duplicates).")

if __name__ == "__main__":
    asyncio.run(main())
