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
    if not time_str or time_str.strip().lower() in ("all day", "ongoing"):
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
    creds_dict = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
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
    time_info = df["Time"].astype(str).apply(_split_times)
    df[["EVENT START TIME", "EVENT END TIME", "ALL DAY EVENT"]] = pd.DataFrame(time_info.tolist(), index=df.index)

    df["EVENT START DATE"] = pd.to_datetime(
        df["Month"] + " " + df["Day"].astype(str) + " " + df["Year"].astype(str)
    ).dt.strftime("%Y-%m-%d")
    df["EVENT END DATE"] = df["EVENT START DATE"]

    export_df = pd.DataFrame({
        "EVENT NAME": df["Event Name"] + config["event_name_suffix"],
        "EVENT EXCERPT": "",
        "EVENT VENUE NAME": df["Location"],
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

    return csv_path
