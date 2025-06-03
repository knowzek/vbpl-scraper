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

    rows = sheet.get_all_values()
    headers = rows[0]
    existing_rows = rows[1:]

    # Build dict by Event Link
    link_to_row_index = {row[1]: idx + 2 for idx, row in enumerate(existing_rows) if len(row) > 1}
    existing_data = {row[1]: row for row in existing_rows if len(row) > 1}

    added = 0
    updated = 0
    skipped = 0

    for event in events:
        link = event.get("Event Link", "")
        if not link:
            print(f"⚠️ Skipping malformed event: {event}")
            skipped += 1
            continue

        new_row = [
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
        ]

        if link not in existing_data:
            # New event
            sheet.append_row(new_row, value_input_option="USER_ENTERED")
            added += 1
        else:
            # Check if any field changed
            old_row = existing_data[link]
            if new_row != old_row:
                row_index = link_to_row_index[link]
                sheet.update(f"A{row_index}:J{row_index}", [new_row])
                updated += 1

    print(f"📦 {added} new events added.")
    print(f"🔁 {updated} existing events updated.")
    if skipped:
        print(f"🧹 {skipped} malformed events skipped.")
