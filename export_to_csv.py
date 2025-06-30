import gspread
import pandas as pd
from datetime import datetime
import base64
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import smtplib
from email.mime.text import MIMEText
import re
from config import get_library_config
from constants import LIBRARY_CONSTANTS
from gspread.utils import rowcol_to_a1

def infer_location_from_title(title, name_suffix_map):
    match = re.search(r"@ ([\w\- ]+)", title)
    if not match:
        return ""
    short_name = match.group(1).strip()
    for full, short in name_suffix_map.items():
        if short_name.lower() in short.lower():
            return full
    return ""

# === UTILITY FUNCTIONS ===
def _format_time(raw: str) -> str:
    if not raw:
        return ""
    txt = raw.lower().replace("–", "-").replace("—", "-").replace(".", "")
    txt = re.sub(r"(\d)([ap]m)", r"\1 \2", txt).strip()
    for fmt in ("%I:%M %p", "%I %p"):
        try:
            return datetime.strptime(txt, fmt).strftime("%-I:%M %p") if ":" in txt else datetime.strptime(txt, fmt).strftime("%-I %p")
        except ValueError:
            continue
    return txt.upper()

def _split_times(time_str: str):
    if not time_str or time_str.strip().lower() in ("all day", "all day event", "ongoing"):
        return "", "", "TRUE"
    parts = re.split(r"\s*[-–—]\s*", time_str)
    start = _format_time(parts[0] if parts else "")
    end = _format_time(parts[1] if len(parts) > 1 else "")
    return start, end, "FALSE"

def _ascii_quotes(val):
    if not isinstance(val, str):
        return val
    return val.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')

def upload_csv_to_drive(csv_path, creds, folder_id):
    drive_service = build("drive", "v3", credentials=creds)
    file_metadata = {"name": os.path.basename(csv_path), "parents": [folder_id]}
    media = MediaFileUpload(csv_path, mimetype="text/csv")
    uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    file_id = uploaded_file.get("id")
    return f"https://drive.google.com/file/d/{file_id}/view"

def send_notification_email(file_url, subject, recipient):
    smtp_user = os.environ["SMTP_USERNAME"]
    smtp_pass = os.environ["SMTP_PASSWORD"]

    msg = MIMEText(f"A new CSV export is ready:\n\n{file_url}")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = recipient

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)

    print(f"📬 Email sent to {recipient}")

# === EXPORT FUNCTION ===
def export_events_to_csv(library="vbpl"):
    config = get_library_config(library)
    npl_suffixes = config.get("name_suffix_map", {})
    constants = LIBRARY_CONSTANTS.get(library, {})
    venue_names = constants.get("venue_names", {})
    name_suffix_map = constants.get("name_suffix_map", {})
    creds = service_account.Credentials.from_service_account_file(
        "/etc/secrets/GOOGLE_APPLICATION_CREDENTIALS_JSON",
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/gmail.send"
        ]
    )

    client = gspread.authorize(creds)
    sheet = client.open(config["spreadsheet_name"]).worksheet(config["worksheet_name"])
    df = pd.DataFrame(sheet.get_all_records())

    # Ensure all required columns exist in the DataFrame even if the sheet doesn't have them yet
    required_columns = [
        "Event Name", "Location", "Categories", "Program Type", "Series", "Event Description",
        "Event Link", "Month", "Day", "Year", "Event End Date", "Site Sync Status",
        "Venue", "EVENT START DATE", "EVENT START TIME", "EVENT END DATE", "EVENT END TIME", "ALL DAY EVENT"
    ]
    
    for col in required_columns:
        if col not in df.columns:
            print(f"🛠️ Creating missing column: {col}")
            df[col] = ""
        else:
            df[col] = df[col].fillna("").astype(str)

    original_row_count = len(df)


    print("\n🔎 Column counts before filtering:")
    for col in [
        "Event Name", "Venue", "EVENT START DATE", "EVENT START TIME", "EVENT END DATE",
        "EVENT END TIME", "ALL DAY EVENT", "Categories", "Event Link", "Event Description"
    ]:
        if col not in df.columns:
            print(f"❌ Missing column: {col}")
        else:
            print(f"{col}: {len(df[col])}")

    # ✅ Ensure required columns exist, even if the sheet is empty or missing data
    required_columns = [
        "Event Name", "Location", "Categories", "Program Type", "Series", "Event Description",
        "Event Link", "Month", "Day", "Year", "Event End Date", "Site Sync Status"
    ]
    for col in required_columns:
        if col not in df.columns:
            df[col] = ""
    
    # Also pre-create output columns to prevent mismatched lengths later
    for col in ["Venue", "EVENT START DATE", "EVENT START TIME", "EVENT END DATE",
                "EVENT END TIME", "ALL DAY EVENT"]:
        df[col] = ""
    
    # ✅ Now do filtering
    df = df[df["Site Sync Status"].fillna("").str.strip().str.lower() == "new"]
    if df.empty:
        print("🚫  No new events to export.")
        return

    df = df[~df["Ages"].fillna("").str.strip().eq("Adults 18+")]
    # Exclude events labeled "Classes & Workshops"
    df = df[~df["Program Type"].fillna("").str.contains("Classes & Workshops", case=False)]
    df = df[~df["Categories"].fillna("").str.contains("Classes & Workshops", case=False)]

    time_info = df["Time"].astype(str).apply(_split_times)
    time_df = pd.DataFrame(time_info.tolist(), index=df.index, columns=["start", "end", "all_day"])
    df[["EVENT START TIME", "EVENT END TIME"]] = time_df[["start", "end"]]
    df["ALL DAY EVENT"] = time_df["all_day"]
    df["Site Sync Status"] = "on site"

    # Clear times if all-day event is TRUE
    df.loc[df["ALL DAY EVENT"] == "TRUE", ["EVENT START TIME", "EVENT END TIME"]] = ["", ""]

    df["EVENT START DATE"] = pd.to_datetime(
        df["Month"] + " " + df["Day"].astype(str) + " " + df["Year"].astype(str)
    ).dt.strftime("%Y-%m-%d")
    df["EVENT END DATE"] = df["Event End Date"] if "Event End Date" in df.columns else df["EVENT START DATE"]

    # Sanitize and format event titles
    suffix = config.get("event_name_suffix", "")

    # Fix missing locations using @Title pattern
    df["Location"] = df.apply(
        lambda row: infer_location_from_title(row["Event Name"], name_suffix_map)
        if not str(row["Location"]).strip() else row["Location"],
        axis=1
    )

    # Format event title with deduplication
    def format_event_title(row):
        name = re.sub(r"\s+at\s+.*", "", row["Event Name"]).strip()
        loc = row["Location"].strip()
        display_loc = name_suffix_map.get(loc, loc)
    
        cleaned_name = name
        if f"({display_loc})" not in name and suffix not in name:
            cleaned_name = f"{name} at {display_loc}"
    
        if suffix not in cleaned_name:
            cleaned_name += f" {suffix}"
    
        return cleaned_name.strip()
    
    df["Event Name"] = df.apply(format_event_title, axis=1)
    df["Venue"] = df["Location"].apply(
        lambda loc: venue_names.get(loc.strip(), name_suffix_map.get(loc.strip(), loc.strip()))
    )
    
    # ✅ Apply sync status AFTER all cleaning
    df["Site Sync Status"] = "on site"

    # Ensure missing columns are filled with empty strings to match row count
    df["Categories"] = df["Categories"].fillna("")
    df["Program Type"] = df["Program Type"].fillna("")
    df["Series"] = df["Series"].fillna("")
    df["Event Description"] = df["Event Description"].fillna("")

    # Ensure missing columns are filled and aligned
    required_cols = [
        "Event Name", "Venue", "EVENT START DATE", "EVENT START TIME", "EVENT END DATE",
        "EVENT END TIME", "ALL DAY EVENT", "Categories", "Event Link", "Event Description"
    ]
    
    # ✅ Sanity check before building the DataFrame
    for col in [
        "Event Name", "Venue", "EVENT START DATE", "EVENT START TIME", "EVENT END DATE",
        "EVENT END TIME", "ALL DAY EVENT", "Categories", "Event Link", "Event Description"
    ]:
        if col not in df.columns:
            print(f"❌ Missing column: {col}")
        else:
            print(f"{col}: {len(df[col])}")

# Ensure export columns are same length by filling missing values
    expected_export_cols = [
        "Event Name", "Venue", "EVENT START DATE", "EVENT START TIME", "EVENT END DATE",
        "EVENT END TIME", "ALL DAY EVENT", "Categories", "Event Link", "Event Description"
    ]

    # Final length check
    print("🔍 Final export column lengths:")
    for col in expected_export_cols:
        print(f"{col}: {len(df[col])}")
    
    for col in expected_export_cols:
        if col not in df.columns:
            df[col] = ""
        else:
            df[col] = df[col].fillna("").astype(str)
    
    export_df = pd.DataFrame({
        "EVENT NAME": df["Event Name"],
        "EVENT EXCERPT": "",
        "EVENT VENUE NAME": df["Venue"],
        "EVENT ORGANIZER NAME": config["organizer_name"],
        "EVENT START DATE": df["EVENT START DATE"],
        "EVENT START TIME": df["EVENT START TIME"],
        "EVENT END DATE": df["EVENT END DATE"],
        "EVENT END TIME": df["EVENT END TIME"],
        "ALL DAY EVENT": df["ALL DAY EVENT"],
        "TIMEZONE": "America/New_York",
        "HIDE FROM EVENT LISTINGS": "FALSE",
        "STICKY IN MONTH VIEW": "FALSE",
        "EVENT CATEGORY": df["Categories"],
        "EVENT TAGS": "",
        "EVENT COST": "",
        "EVENT CURRENCY SYMBOL": "$",
        "EVENT CURRENCY POSITION": "",
        "EVENT ISO CURRENCY CODE": "USD",
        "EVENT FEATURED IMAGE": "",
        "EVENT WEBSITE": df["Event Link"],
        "EVENT SHOW MAP LINK": "TRUE",
        "EVENT SHOW MAP": "TRUE",
        "ALLOW COMMENTS": "FALSE",
        "ALLOW TRACKBACKS AND PINGBACKS": "FALSE",
        "EVENT DESCRIPTION": df["Event Description"]
    })

    str_cols = export_df.select_dtypes(include="object").columns
    export_df[str_cols] = export_df[str_cols].applymap(_ascii_quotes)

    csv_path = f"events_for_upload_{library}.csv"
    export_df.to_csv(csv_path, index=False)
    print(f"✅ Exported {len(export_df)} events to CSV (from {original_row_count} original rows)")

    file_url = upload_csv_to_drive(csv_path, creds, config["drive_folder_id"])
    send_notification_email(file_url, config["email_subject"], config["email_recipient"])
    # ✅ Mark exported rows as "on site" in the sheet
    site_sync_col = df.columns.get_loc("Site Sync Status")  # column P, zero-indexed
    values = sheet.get_all_values()

    # Build a map from Event Link → Sheet Row Number
    link_col_idx = df.columns.get_loc("Event Link")
    event_link_to_row = {}
    
    for i, row in enumerate(values[1:], start=2):  # start=2 because sheet rows are 1-based
        if len(row) > link_col_idx:
            link = row[link_col_idx].strip()
            if link:
                event_link_to_row[link] = i
    
    # Start after header (row 2 onward)

    # Prepare batch updates
    updates = []
    for link in df["Event Link"]:
        row_num = event_link_to_row.get(link.strip())
        if row_num:
            cell = rowcol_to_a1(row_num, site_sync_col + 1)
            updates.append({"range": cell, "values": [["on site"]]})
    
    # Perform a batch update
    if updates:
        sheet.batch_update([{"range": u["range"], "values": u["values"]} for u in updates])

    return csv_path

if __name__ == "__main__":
    LIBRARIES = ["vbpl", "npl", "chpl"]  # Add more libraries as needed

    for lib in LIBRARIES:
        print(f"\n📁 Exporting events for: {lib.upper()}")
        try:
            export_events_to_csv(lib)
        except Exception as e:
            print(f"❌ Failed to export for {lib}: {e}")

