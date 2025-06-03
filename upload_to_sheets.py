import gspread
import json
import os
from google.oauth2.service_account import Credentials

SPREADSHEET_NAME = "Virginia Beach Library Events"
WORKSHEET_NAME = "VBPL Events"

def connect_to_sheet(sheet_name, worksheet_name):
    creds_json = os.environ["GOOGLE_SHEETS_CREDS"]
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name).worksheet(worksheet_name)
    return sheet

def upload_events_to_sheet(events, sheet=None):
    if sheet is None:
        sheet = connect_to_sheet(SPREADSHEET_NAME, WORKSHEET_NAME)

    existing_links = {row[1] for row in sheet.get_all_values()[1:] if len(row) > 1}
    print(f"📄 {len(existing_links)} existing links in sheet.")

    new_rows = []
    for event in events:
        if event["Event Link"] not in existing_links:
            new_rows.append([
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
            ])

    if new_rows:
        sheet.append_rows(new_rows, value_input_option="USER_ENTERED")
        print(f"📦 Added {len(new_rows)} new rows.")
    else:
        print("✅ No new events to add.")
