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


# === MAIN EXPORT FUNCTION ===
def export_events_to_csv():
    sheet = get_sheet()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    original_row_count = len(df)
    print("Before filter:\n", df[["Event Name", "Ages", "Site Sync Status"]])

    print("Step 1: Initial rows:", len(df))

    # === FILTERING ===
    df['Ages'] = df['Ages'].astype(str).str.strip()
    df = df[df['Ages'] != "Adults 18+"]
    print("Step 2: After filtering out 'Adults 18+':", len(df))
    
    df['Site Sync Status'] = df['Site Sync Status'].astype(str).str.strip().str.lower()
    df = df[~df['Site Sync Status'].isin(['on site', 'updated'])]
    print("Step 3: After filtering 'on site' / 'updated':", len(df))
    
    # === NORMALIZE LOCATION ===
    df['Location'] = df['Location'].astype(str).str.strip()
    df['Location Mapped'] = df['Location'].map(LOCATION_MAP)
    print("⚠️ Unmatched locations:\n", df[df['Location Mapped'].isna()]['Location'].unique())
    print("Step 4: Rows with mapped locations:", df['Location Mapped'].notna().sum())
    
    df = df[df['Location Mapped'].notna()]
    df['Location'] = df['Location Mapped']
    df.drop(columns=['Location Mapped'], inplace=True)
    print("Step 5: Final export row count:", len(df))

    # === FORMAT START DATE ===
    df['EVENT START DATE'] = pd.to_datetime(df['Month'] + ' ' + df['Day'].astype(str) + ' ' + df['Year'].astype(str))
    df['EVENT START DATE'] = df['EVENT START DATE'].dt.strftime('%Y-%m-%d')

    # === CREATE CSV FIELDS ===
    export_df = pd.DataFrame({
        'EVENT NAME': df['Event Name'] + ' (Virginia Beach)',
        'EVENT EXCERPT': '',
        'EVENT VENUE NAME': df['Location'],
        'EVENT ORGANIZER NAME': '',
        'EVENT START DATE': df['EVENT START DATE'],
        'EVENT START TIME': df['Time'],
        'EVENT END DATE': df['EVENT START DATE'],
        'EVENT END TIME': '',
        'ALL DAY EVENT': 0,
        'TIMEZONE': 'America/New_York',
        'HIDE FROM EVENT LISTINGS': 0,
        'STICKY IN MONTH VIEW': 0,
        'EVENT CATEGORY': df['Categories'],
        'EVENT TAGS': '',
        'EVENT COST': '',
        'EVENT CURRENCY SYMBOL': '$',
        'EVENT CURRENCY POSITION': 'prefix',
        'EVENT ISO CURRENCY CODE': 'USD',
        'EVENT FEATURED IMAGE': '',
        'EVENT WEBSITE': df['Event Link'],
        'EVENT SHOW MAP LINK': 1,
        'EVENT SHOW MAP': 1,
        'ALLOW COMMENTS': 1,
        'ALLOW TRACKBACKS AND PINGBACKS': 1,
        'EVENT DESCRIPTION': df['Event Description']
    })

    # === SAVE CSV ===
    export_df.to_csv(CSV_EXPORT_PATH, index=False)
    print(f"✅ Exported {len(export_df)} events to CSV (from {original_row_count} original rows)")

    # === UPDATE SHEET: Set Site Sync Status to 'on site' for these ===
    update_indices = df.index + 2  # account for header row + 0-index
    for i in update_indices:
       sheet.update(f"P{i}", [["on site"]])

    # === Upload to Drive and Email ===
    file_url = upload_csv_to_drive(CSV_EXPORT_PATH)
    send_notification_email(file_url)

if __name__ == "__main__":
    export_events_to_csv()
