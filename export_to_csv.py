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
    original_row_count = len(df)

    df = df[df["Site Sync Status"].fillna("").str.strip().str.lower() == "new"]
    if df.empty:
        print("🚫  No new events to export.")
        return

    df = df[~df["Ages"].fillna("").str.strip().eq("Adults 18+")]
    # Exclude events labeled "Classes & Workshops"
    df = df[~df["Program Type"].fillna("").str.contains("Classes & Workshops", case=False)]
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
    df["EVENT END DATE"] = df.get("Event End Date", df["EVENT START DATE"])

    # Sanitize and format event titles
    suffix = config.get("event_name_suffix", "")

    def format_event_title(row):
        name = row["Event Name"]
        name = re.sub(r"\s*@\s*[^@,;:\\/]+", "", name, flags=re.IGNORECASE).strip()
        name = re.sub(r"\s+at\s+.*", "", name, flags=re.IGNORECASE).strip()
        loc = row["Location"].strip()
        display_loc = name_suffix_map.get(loc, loc)
        suffix = config.get("event_name_suffix", "")
        if name.lower().endswith(display_loc.lower()):
            return f"{name}{suffix}"
        return f"{name} at {display_loc}{suffix}"

    # Fix missing locations using @Title pattern
    df["Location"] = df.apply(
        lambda row: infer_location_from_title(row["Event Name"], npl_suffixes)
        if not str(row["Location"]).strip() else row["Location"],
        axis=1
    )

    # Format event title with deduplication
    def format_event_title(row):
        name = re.sub(r"\s+at\s+.*", "", row["Event Name"]).strip()
        loc = row["Location"].strip()
        display_loc = npl_suffixes.get(loc, loc)
    
        cleaned_name = name
        if f"({display_loc})" not in name and "(Norfolk)" not in name:
            cleaned_name = f"{name} at {display_loc}"
    
        if "(Norfolk)" not in cleaned_name:
            cleaned_name += " (Norfolk)"
    
        return cleaned_name
    
    df["Event Name"] = df.apply(format_event_title, axis=1)
    df["Venue"] = df["Location"].map(venue_names).fillna(df["Location"])
    
    # ✅ Apply sync status AFTER all cleaning
    df["Site Sync Status"] = "on site"

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
    
    # Start after header (row 2 onward)
    for i, row in enumerate(values[1:], start=2):
        if row[site_sync_col].strip().lower() == "new":
            sheet.update_cell(i, site_sync_col + 1, "on site")  # Google Sheets uses 1-based indexing

    return csv_path

if __name__ == "__main__":
    LIBRARIES = ["vbpl", "npl", "chpl"]  # Add more libraries as needed

    for lib in LIBRARIES:
        print(f"\n📁 Exporting events for: {lib.upper()}")
        try:
            export_events_to_csv(lib)
        except Exception as e:
            print(f"❌ Failed to export for {lib}: {e}")

