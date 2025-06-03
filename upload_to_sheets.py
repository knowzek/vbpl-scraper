import os
import json
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_NAME = "Virginia Beach Library Events"
WORKSHEET_NAME = "VBPL Events"
LOG_WORKSHEET_NAME = "VBPL Log"

def connect_to_sheet(spreadsheet_name, worksheet_name):
    creds = Credentials.from_service_account_file(
        "/etc/secrets/GOOGLE_APPLICATION_CREDENTIALS_JSON",
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    client = gspread.authorize(creds)
    return client.open(spreadsheet_name).worksheet(worksheet_name)

def upload_events_to_sheet(events, sheet=None, mode="full"):
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

    # Log results to VBPL Log tab
    try:
        log_sheet = connect_to_sheet(SPREADSHEET_NAME, LOG_WORKSHEET_NAME)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_row = [now, mode, added, updated, skipped]
        log_sheet.append_row(log_row, value_input_option="USER_ENTERED")
        print("📝 Logged summary to 'VBPL Log' tab.")
    except Exception as e:
        print(f"⚠️ Failed to log to VBPL Log tab: {e}")

    print(f"📦 {added} new events added.")
    print(f"🔁 {updated} existing events updated.")
    if skipped:
        print(f"🧹 {skipped} malformed events skipped.")
