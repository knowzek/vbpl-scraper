import gspread
import pandas as pd
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from email.mime.text import MIMEText
import base64
import os
import json
from google.oauth2 import service_account

# === CONFIG ===
SPREADSHEET_NAME = "Virginia Beach Library Events"
WORKSHEET_NAME = "VBPL Events"
CSV_EXPORT_PATH = "events_for_upload.csv"
DRIVE_FOLDER_ID = "1MrUjkl8EirZpoR2sT80UYc0ECCEMI-W1"  # Replace with your actual folder ID
EMAIL_RECIPIENT = "knowzek@gmail.com"
EMAIL_SUBJECT = "new csv export for upload ready"

# === AUTH ===
CREDENTIALS_JSON = os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"]
creds_dict = json.loads(CREDENTIALS_JSON)
creds = service_account.Credentials.from_service_account_info(
    creds_dict,
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/gmail.send"
    ]
)

# === LOCATION NORMALIZATION ===
# Reverse mapping: from full labels → to simplified names
LOCATION_MAP = {
    "Library Branch:Oceanfront Area Library": "Oceanfront Area Library",
    "Library Branch:Meyera E. Oberndorf Central Library": "MEO Central Library",
    "Library Branch:TCC/City Joint-Use Library": "TCC Joint-Use Library",
    "Library Branch:Princess Anne Area Library": "Princess Anne Area Library",
    "Library Branch:Bayside Area Library": "Bayside Area Library",
    "Library Branch:Pungo-Blackwater Library": "Pungo Blackwater Library",
    "Library Branch:Windsor Woods Area Library": "Windsor Woods Area Library",
    "Library Branch:Great Neck Area Library": "Great Neck Area Library",
    "Library Branch:Kempsville Area Library": "Kempsville Area Library"
}

# === CONNECT TO SHEET ===
def get_sheet():
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME).worksheet(WORKSHEET_NAME)
    return sheet

# === UPLOAD CSV TO GOOGLE DRIVE ===
def upload_csv_to_drive(csv_path):
    drive_service = build("drive", "v3", credentials=creds)
    file_metadata = {"name": "events_for_upload.csv", "parents": [DRIVE_FOLDER_ID]}
    media = MediaFileUpload(csv_path, mimetype="text/csv")
    uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    file_id = uploaded_file.get("id")
    return f"https://drive.google.com/file/d/{file_id}/view"

# === SEND EMAIL VIA GMAIL API ===
import smtplib
from email.mime.text import MIMEText

def send_notification_email(file_url):
    smtp_user = os.environ["SMTP_USERNAME"]
    smtp_pass = os.environ["SMTP_PASSWORD"]

    msg = MIMEText(f"A new CSV export is ready:\n\n{file_url}")
    msg["Subject"] = EMAIL_SUBJECT
    msg["From"] = smtp_user
    msg["To"] = EMAIL_RECIPIENT

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)

    print(f"📬 Email sent to {EMAIL_RECIPIENT}")


# ─── helper functions ──────────────────────────────────────────────────────────
import re
from datetime import datetime

def _format_time(raw: str) -> str:
    """
    Normalises a raw time string to `H:MM AM` / `H AM` with uppercase meridiem.
    Accepts inputs such as '3:30 pm', '8 PM', '2 pm', etc.
    Falls back to the cleaned string if parsing fails.
    """
    if not raw:
        return ""
    txt = raw.lower().replace(" ", " ").replace("–", "-").replace("—", "-").replace(".", "")
    txt = re.sub(r"(\d)([ap]m)", r"\1 \2", txt).strip()            # ensure space before am/pm
    for fmt in ("%I:%M %p", "%I %p"):
        try:
            return datetime.strptime(txt, fmt).strftime("%-I:%M %p") \
                   if ":" in txt else datetime.strptime(txt, fmt).strftime("%-I %p")
        except ValueError:
            continue
    return txt.upper()                                             # fallback – already readable

def _split_times(time_str: str):
    """
    Splits a VBPL time string like '3:30 PM – 4:30 PM' (or variants) into
    clean start- and end-time components. Returns (start, end, all_day_flag).
    """
    if not time_str or time_str.strip().lower() in ("all day", "ongoing"):
        return "", "", "TRUE"                                       # treat as an all-day event
    parts = re.split(r"\s*[-–—]\s*", time_str)                      # dash/en-dash/em-dash
    start = _format_time(parts[0] if parts else "")
    end   = _format_time(parts[1] if len(parts) > 1 else "")
    return start, end, "FALSE"

# ─── main export function ──────────────────────────────────────────────────────
def export_events_to_csv():
    sheet = get_sheet()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)                                         # ← existing load
    original_row_count = len(df)

    # ── KEEP only rows whose Site Sync Status is "new" ──
    df = df[df["Site Sync Status"].fillna("").str.strip().str.lower() == "new"]
    if df.empty:
        print("🚫  No new events to export.")
        return
        
    # ── drop events whose Ages column is ONLY "Adults 18+" ──
    df = df[~df["Ages"].fillna("").str.strip().eq("Adults 18+")]

    # ── NEW: extract start/end/all-day from the “Time” column ──
    time_info = df["Time"].astype(str).apply(_split_times)          # returns tuples
    df[["EVENT START TIME", "EVENT END TIME", "ALL DAY EVENT"]] = \
        pd.DataFrame(time_info.tolist(), index=df.index)

    # ── format EVENT START / END DATE (unchanged) ──
    df["EVENT START DATE"] = pd.to_datetime(
        df["Month"] + " " + df["Day"].astype(str) + " " + df["Year"].astype(str)
    ).dt.strftime("%Y-%m-%d")
    df["EVENT END DATE"] = df["EVENT START DATE"]                    # same-day events

    # ── assemble export dataframe ──
    export_df = pd.DataFrame({
        "EVENT NAME": df["Event Name"] + " (Virginia Beach)",
        "EVENT EXCERPT": "",
        "EVENT VENUE NAME": df["Location"],
        "EVENT ORGANIZER NAME": "",
        "EVENT START DATE": df["EVENT START DATE"],
        "EVENT START TIME": df["EVENT START TIME"],                 # ★ Column F
        "EVENT END DATE": df["EVENT END DATE"],
        "EVENT END TIME": df["EVENT END TIME"],                     # ★ Column H
        "ALL DAY EVENT": df["ALL DAY EVENT"],                       # ★ Column I  (TRUE/FALSE)
        "TIMEZONE": "America/New_York",
        "HIDE FROM EVENT LISTINGS": "FALSE",                        # ★ Column K
        "STICKY IN MONTH VIEW": "FALSE",
        "EVENT CATEGORY": df["Categories"],
        "EVENT TAGS": "",
        "EVENT COST": "",
        "EVENT CURRENCY SYMBOL": "$",
        "EVENT CURRENCY POSITION": "",                              # ★ Column Q (blank)
        "EVENT ISO CURRENCY CODE": "USD",
        "EVENT FEATURED IMAGE": "",
        "EVENT WEBSITE": df["Event Link"],
        "EVENT SHOW MAP LINK": "TRUE",                              # ★ Column U
        "EVENT SHOW MAP": "TRUE",                                   # ★ Column V
        "ALLOW COMMENTS": "FALSE",                                  # ★ Column W
        "ALLOW TRACKBACKS AND PINGBACKS": "FALSE",                  # ★ Column X
        "EVENT DESCRIPTION": df["Event Description"],
    })

    # === SAVE CSV ===
    export_df.to_csv(CSV_EXPORT_PATH, index=False)
    print(f"✅ Exported {len(export_df)} events to CSV (from {original_row_count} original rows)")

    # ---------- STEP 2: update ‘Site Sync Status’ for ONLY the rows we just exported ----------
    # (df now contains only the rows we exported)
    rows_to_mark = sorted(df.index + 2)   # convert DataFrame index → sheet row numbers (add header + 0-index)

    if rows_to_mark:                      # skip if nothing was exported
        def contiguous_groups(nums):
            """Yield (start, end) pairs for consecutive runs, e.g. [5,6,7,12,13] → (5,7), (12,13)."""
            start = prev = nums[0]
            for n in nums[1:]:
                if n == prev + 1:
                    prev = n
                else:
                    yield (start, prev)
                    start = prev = n
            yield (start, prev)

        for start, end in contiguous_groups(rows_to_mark):
            range_name = f"P{start}:P{end}"                # e.g. "P14:P28"
            values     = [["on site"]] * (end - start + 1) # one “on site” per row
            sheet.update(
                range_name=range_name,
                values=values,
                value_input_option="USER_ENTERED"
            )

    # ---------- DONE ----------

    # === Upload to Drive and Email ===
    file_url = upload_csv_to_drive(CSV_EXPORT_PATH)
    send_notification_email(file_url)

if __name__ == "__main__":
    export_events_to_csv()
