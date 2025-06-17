from datetime import datetime
import os
import gspread
from google.oauth2.service_account import Credentials
import traceback

SPREADSHEET_NAME = "Virginia Beach Library Events"
WORKSHEET_NAME = "VBPL Events"
LOG_WORKSHEET_NAME = "VBPL Log"

PROGRAM_TYPE_TO_CATEGORIES = {
    "Storytimes & Early Learning": "Event Location - Virginia Beach, Audience - Family Event, List - Storytimes",
    "STEAM": "Event Location - Virginia Beach, List - STEM/STEAM, Audience - Family Event",
    "Computers & Technology": "Event Location - Virginia Beach, Audience - Teens, Audience - Family Event",
    "Workshops & Lectures": "Event Location - Virginia Beach, Audience - Family Event",
    "Discussion Groups": "Event Location - Virginia Beach, Audience - Family Event",
    "Arts & Crafts": "Event Location - Virginia Beach, Audience - Family Event",
    "Hobbies": "Event Location - Virginia Beach, Audience - Family Event",
    "Books & Authors": "Event Location - Virginia Beach, Audience - Family Event",
    "Culture": "Event Location - Virginia Beach, Audience - Family Event",
    "History & Genealogy": "Event Location - Virginia Beach, Audience - Family Event"
}

def connect_to_sheet(spreadsheet_name, worksheet_name):
    creds = Credentials.from_service_account_file(
        "/etc/secrets/GOOGLE_APPLICATION_CREDENTIALS_JSON",
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    client = gspread.authorize(creds)
    return client.open(spreadsheet_name).worksheet(worksheet_name)

def normalize(row):
    return [cell.strip() for cell in row[:13]] + [""] * (13 - len(row))  # A–M fields

def upload_events_to_sheet(events, sheet=None, mode="full"):
    try:
        if sheet is None:
            sheet = connect_to_sheet(SPREADSHEET_NAME, WORKSHEET_NAME)

        rows = sheet.get_all_values()
        headers = rows[0]
        existing_rows = rows[1:]

        # Pad each row to 16 columns
        for i, row in enumerate(existing_rows):
            if len(row) < 16:
                print(f"[WARN] Row {i + 2} too short: {len(row)} cols → {row}")
                row += [""] * (16 - len(row))

        link_to_row_index = {row[1]: idx + 2 for idx, row in enumerate(existing_rows) if len(row) > 1}
        existing_data = {row[1]: row for row in existing_rows if len(row) > 1}

        added = 0
        updated = 0
        skipped = 0

        new_rows = []
        update_requests = []

        for event in events:
            try:
                link = event.get("Event Link", "")
                if not link:
                    print(f"⚠️ Skipping malformed event (missing link): {event}")
                    skipped += 1
                    continue

                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                program_type = event.get("Program Type", "")
                categories = PROGRAM_TYPE_TO_CATEGORIES.get(program_type, "")

                # ── AGE-BASED AUDIENCE TAGS ──────────────────────────────────
                ages_raw = event.get("Ages", "")
                age_tags = []
                nums = [int(n) for n in re.findall(r"\d+", ages_raw)]

                if nums:
                    min_age, max_age = min(nums), max(nums)

                    # 0-2  ⇒ Toddler / Infant
                    if max_age <= 2:
                        age_tags.append("Audience - Toddler/Infant")

                    # ≤4   ⇒ Parent & Me
                    if max_age <= 4:
                        age_tags.append("Audience - Parent & Me")

                    # contains 3 or 4 ⇒ Preschool Age
                    if any(a in (3, 4) for a in nums):
                        age_tags.append("Audience - Preschool Age")

                    # 5-12 range ⇒ School Age
                    if max_age >= 5 and min_age <= 12:
                        age_tags.append("Audience - School Age")

                    # ≥13  ⇒ Teens
                    if max_age >= 13:
                        age_tags.append("Audience - Teens")

                # merge with existing program-type categories, de-dupe, strip rogue bytes
                if age_tags:
                    base = [c.strip() for c in categories.split(",") if c.strip()]
                    combined = base + age_tags
                    categories = ", ".join(dict.fromkeys(combined))          # ordered de-dup
                categories = categories.replace("\u00A0", " ").replace("Â", "").strip()
                # ─────────────────────────────────────────────────────────────

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
                if link in existing_data and new_core != existing_core:
                    status = "updated"
                elif link in existing_data:
                    status = existing_row[14]

                site_sync_status = existing_row[15]
                if link not in existing_data:
                    site_sync_status = "new"
                elif new_core != existing_core:
                    site_sync_status = "updated" if site_sync_status == "on site" else "new"
                else:
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
            print("📝 Logged summary to 'VBPL Log' tab.")
        except Exception as e:
            print(f"⚠️ Failed to log to VBPL Log tab: {e}")

        print(f"📦 {added} new events added.")
        print(f"🔁 {updated} existing events updated.")
        if skipped:
            print(f"🧹 {skipped} malformed events skipped.")

    except Exception as e:
        print(f"❌ ERROR during upload_events_to_sheet: {e}")
        traceback.print_exc()
