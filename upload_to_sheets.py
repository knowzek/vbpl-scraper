import os
import json
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_NAME = "Virginia Beach Library Events"
WORKSHEET_NAME = "VBPL Events"

def connect_to_sheet(spreadsheet_name, worksheet_name):
    creds = Credentials.from_service_account_file(
        "/etc/secrets/GOOGLE_APPLICATION_CREDENTIALS_JSON",
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    client = gspread.authorize(creds)
    return client.open(spreadsheet_name).worksheet(worksheet_name)
    client = gspread.authorize(creds)
    sheet = client.open(spreadsheet_name).worksheet(worksheet_name)
    return sheet

def upload_events_to_sheet(events, sheet=None):
    if sheet is None:
        sheet = connect_to_sheet(SPREADSHEET_NAME, WORKSHEET_NAME)

    existing_links = {row[1] for row in sheet.get_all_values()[1:] if len(row) > 1}
    print(f"📄 {len(existing_links)} existing links in sheet.")

    new_rows = []
    skipped = 0

    for event in events:
        link = event.get("Event Link", "")
        if not link:
            print(f"⚠️ Skipping malformed event (missing link): {event}")
            skipped += 1
            continue

        if link not in existing_links:
            new_rows.append([
                event.get("Event Name", ""),
                link,
                event.get("Event Status", ""),
                event.get("Time", ""),
                event.get("Ages", ""),
                event.get("Location", ""),
                event.get("Month", ""),
                event.get("Day", ""),
                event.get("Year", ""),
                event.get("Event Description", "")
            ])

    if new_rows:
        sheet.append_rows(new_rows, value_input_option="USER_ENTERED")
        print(f"📦 Added {len(new_rows)} new rows.")
    else:
        print("✅ No new events to add.")

    if skipped:
        print(f"🧹 Skipped {skipped} malformed events.")
