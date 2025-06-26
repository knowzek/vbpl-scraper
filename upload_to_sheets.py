from datetime import datetime
import os
import gspread
from google.oauth2.service_account import Credentials
import traceback
from config import get_library_config
import json
from google.oauth2 import service_account

import re


def _clean_link(url: str) -> str:
    """Return the URL with any '/index.php' fragment removed, preserving one slash."""
    cleaned = (
        url.replace("/index.php/", "/")
           .replace("/index.php", "/")
    )
    return cleaned.replace("://", ":::").replace("//", "/").replace(":::", "://")


def connect_to_sheet(spreadsheet_name, worksheet_name):
    creds = service_account.Credentials.from_service_account_file(
        "/etc/secrets/google.json",  # or whatever path you configured in Render
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    client = gspread.authorize(creds)
    return client.open(spreadsheet_name).worksheet(worksheet_name)

def normalize(row):
    return [cell.strip() for cell in row[:13]] + [""] * (13 - len(row))  # A–M fields


def upload_events_to_sheet(events, library="vbpl", sheet=None, mode="full"):
    config = get_library_config(library)
    SPREADSHEET_NAME = config["spreadsheet_name"]
    WORKSHEET_NAME = config["worksheet_name"]
    LOG_WORKSHEET_NAME = config["log_worksheet_name"]

    PROGRAM_TYPE_TO_CATEGORIES = {
        "Storytimes & Early Learning": f"Event Location - {config['organizer_name']}, Audience - Free Event, Audience - Family Event, List - Storytimes",
        "STEAM": f"Event Location - {config['organizer_name']}, List - STEM/STEAM, Audience - Free Event, Audience - Family Event",
        "Computers & Technology": f"Event Location - {config['organizer_name']}, Audience - Free Event, Audience - Teens, Audience - Family Event",
        "Workshops & Lectures": f"Event Location - {config['organizer_name']}, Audience - Free Event, Audience - Family Event",
        "Discussion Groups": f"Event Location - {config['organizer_name']}, Audience - Free Event, Audience - Family Event",
        "Arts & Crafts": f"Event Location - {config['organizer_name']}, Audience - Free Event, Audience - Family Event",
        "Hobbies": f"Event Location - {config['organizer_name']}, Audience - Free Event, Audience - Family Event",
        "Books & Authors": f"Event Location - {config['organizer_name']}, Audience - Free Event, Audience - Family Event",
        "Culture": f"Event Location - {config['organizer_name']}, Audience - Free Event, Audience - Family Event",
        "History & Genealogy": f"Event Location - {config['organizer_name']}, Audience - Teens, Audience - Free Event"
    }

    try:
        if sheet is None:
            sheet = connect_to_sheet(SPREADSHEET_NAME, WORKSHEET_NAME)

        rows = sheet.get_all_values()
        headers = rows[0]
        existing_rows = rows[1:]

        for i, row in enumerate(existing_rows):
            if len(row) < 16:
                print(f"[WARN] Row {i + 2} too short: {len(row)} cols → {row}")
                row += [""] * (16 - len(row))

        link_to_row_index = {}
        existing_data = {}

        for idx, row in enumerate(existing_rows):
            if len(row) <= 1:
                continue
            clean_link = _clean_link(row[1].strip())
            link_to_row_index[clean_link] = idx + 2
            existing_data[clean_link] = row

        added = 0
        updated = 0
        skipped = 0

        new_rows = []
        update_requests = []

        for event in events:
            try:
                raw_link = (event.get("Event Link", "") or "").strip()
                if not raw_link:
                    print(f"⚠️  Skipping malformed event (missing link): {event.get('Event Name','')}")
                    skipped += 1
                    continue

                link = _clean_link(raw_link)

                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                program_type = event.get("Program Type", "")
                categories = PROGRAM_TYPE_TO_CATEGORIES.get(program_type, "")

                ages_raw = event.get("Ages", "")
                age_tags = []
                nums = [int(n) for n in re.findall(r"\d+", ages_raw)]

                if nums:
                    min_age, max_age = min(nums), max(nums)
                    if max_age <= 2:
                        age_tags.append("Audience - Toddler/Infant")
                    if max_age <= 4:
                        age_tags.append("Audience - Parent & Me")
                    if any(a in (3, 4) for a in nums):
                        age_tags.append("Audience - Preschool Age")
                    if max_age >= 5 and min_age <= 12:
                        age_tags.append("Audience - School Age")
                    if max_age >= 13:
                        age_tags.append("Audience - Teens")

                if age_tags:
                    base = [c.strip() for c in categories.split(",") if c.strip()]
                    combined = base + age_tags
                    categories = ", ".join(dict.fromkeys(combined))
                categories = categories.replace("\u00A0", " ").replace("Â", "").strip()

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
                    event.get("Event Description", ""),
                    event.get("Series", ""),
                    program_type,
                    categories
                ]

                new_core = normalize(row_core)
                existing_row = existing_data.get(link, [""] * 16)
                existing_core = normalize(existing_row)

                status = "new"
                site_sync_status = existing_row[15] if link in existing_data else "new"

                if link in existing_data:
                    existing_vals = {
                        "status": existing_row[2],
                        "month": existing_row[6],
                        "day": existing_row[7],
                        "year": existing_row[8],
                        "time": existing_row[3],
                    }
                    current_vals = {
                        "status": event.get("Event Status", ""),
                        "month": event.get("Month", ""),
                        "day": event.get("Day", ""),
                        "year": event.get("Year", ""),
                        "time": event.get("Time", "")
                    }
                    changed_to_cancelled = (
                        existing_vals["status"].lower() != current_vals["status"].lower()
                        and current_vals["status"].lower() == "cancelled"
                    )
                    date_changed = (
                        existing_vals["month"] != current_vals["month"]
                        or existing_vals["day"] != current_vals["day"]
                        or existing_vals["year"] != current_vals["year"]
                    )
                    time_changed = existing_vals["time"] != current_vals["time"]
                    if changed_to_cancelled or date_changed or time_changed:
                        status = "updates needed"
                        if site_sync_status == "on site":
                            site_sync_status = "updates needed"
                    else:
                        status = existing_row[14]
                        site_sync_status = site_sync_status or ""

                full_row = new_core + [now, status, site_sync_status]

                if link not in existing_data:
                    new_rows.append(full_row)
                    added += 1
                elif new_core != existing_core:
                    row_index = link_to_row_index[link]
                    update_requests.append({
                        "range": f"A{row_index}:Q{row_index}",
                        "values": [full_row]
                    })
                    updated += 1
            except Exception as row_err:
                print(f"❌ Error processing event: {event.get('Event Name')} — {event.get('Event Link')}")
                traceback.print_exc()
                skipped += 1

        if update_requests:
            sheet.batch_update(update_requests)

        if new_rows:
            sheet.append_rows(new_rows, value_input_option="USER_ENTERED")

        try:
            log_sheet = connect_to_sheet(SPREADSHEET_NAME, LOG_WORKSHEET_NAME)
            log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_row = [log_time, mode, added, updated, skipped]
            log_sheet.append_row(log_row, value_input_option="USER_ENTERED")
            print(f"📝 Logged summary to '{LOG_WORKSHEET_NAME}' tab.")
        except Exception as e:
            print(f"⚠️ Failed to log to {LOG_WORKSHEET_NAME} tab: {e}")

        print(f"📦 {added} new events added.")
        print(f"🔁 {updated} existing events updated.")
        if skipped:
            print(f"🧹 {skipped} malformed events skipped.")

    except Exception as e:
        print(f"❌ ERROR during upload_events_to_sheet: {e}")
        traceback.print_exc()
