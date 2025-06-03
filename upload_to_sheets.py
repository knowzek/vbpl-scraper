import os
import json
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_NAME = "Virginia Beach Library Events"
WORKSHEET_NAME = "VBPL Events"

def connect_to_sheet(spreadsheet_name, worksheet_name):
    creds_json = os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"]

    # Write the secret to a file so gspread can use it
    with open("/tmp/credentials.json", "w") as f:
        f.write(creds_json)

    creds = Credentials.from_service_account_file(
        "/tmp/credentials.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"],
    )
    client = gspread.authorize(creds)
    sheet = client.open(spreadsheet_name).worksheet(worksheet_name)
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
