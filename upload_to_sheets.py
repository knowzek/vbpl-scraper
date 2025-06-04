from datetime import datetime
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

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # First 10 data fields (columns A–J)
        row_core = [
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

        # Status logic
        status = "new"
        if link in existing_data and row_core != existing_data[link][:10]:
            status = "updated"
        elif link in existing_data:
            status = existing_data[link][10] or ""

        # Site Sync Status logic
        site_sync_status = existing_data.get(link, [""] * 13)[12]
        if link not in existing_data:
            site_sync_status = "new"
        elif row_core != existing_data[link][:10]:
            site_sync_status = "updated" if site_sync_status == "on site" else "new"
        else:
            site_sync_status = site_sync_status or ""

        # Final row
        new_row = row_core + [now, status, site_sync_status]

        if link not in existing_data:
            sheet.append_row(new_row, value_input_option="USER_ENTERED")
            added += 1
        else:
            if row_core != existing_data[link][:10]:
                row_index = link_to_row_index[link]
                sheet.update(f"A{row_index}:M{row_index}", [new_row])
                updated += 1

    # ✅ Log to VBPL Log tab
    try:
        log_sheet = connect_to_sheet(SPREADSHEET_NAME, LOG_WORKSHEET_NAME)
        log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_row = [log_time, mode, added, updated, skipped]
        log_sheet.append_row(log_row, value_input_option="USER_ENTERED")
        print("📝 Logged summary to 'VBPL Log' tab.")
    except Exception as e:
        print(f"⚠️ Failed to log to VBPL Log tab: {e}")

    print(f"📦 {added} new events added.")
    print(f"🔁 {updated} existing events updated.")
    if skipped:
        print(f"🧹 {skipped} malformed events skipped.")
