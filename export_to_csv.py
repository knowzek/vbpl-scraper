import gspread
import pandas as pd
from datetime import datetime, timedelta
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
import unicodedata
from email.mime.base import MIMEBase
from email import encoders
from email.mime.multipart import MIMEMultipart

def send_notification_email_with_attachment(file_path, subject, recipient):
    smtp_user = os.environ["SMTP_USERNAME"]
    smtp_pass = os.environ["SMTP_PASSWORD"]

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = recipient
    msg.attach(MIMEText("Your new CSV export is attached."))

    # Attach file
    with open(file_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(file_path)}")
        msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)

    print(f"📧 Email with attachment sent to {recipient}")


def _ascii_normalize(val):
    if not isinstance(val, str):
        return val
    # Normalize to NFKD and encode to ASCII, ignoring errors
    return unicodedata.normalize("NFKD", val).encode("ascii", "ignore").decode("ascii")


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

MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

def _parse_time_with_dates(s):
    """
    Parse strings like:
      'September 6 at 9:00 am - September 7 at 6:00 pm'
    Return dict or None:
      {"start_time": "9:00 AM", "end_time": "6:00 PM", "end_month": 9, "end_day": 7}
    """
    if not s:
        return None
    pat = re.compile(
        r'(?i)^\s*([A-Za-z]+)\s+(\d{1,2})\s+at\s+([0-9]{1,2}(?::[0-9]{2})?\s*[ap]\.?m\.?)\s*[-–—]\s*([A-Za-z]+)\s+(\d{1,2})\s+at\s+([0-9]{1,2}(?::[0-9]{2})?\s*[ap]\.?m\.?)\s*$'
    )
    m = pat.match(s.strip())
    if not m:
        return None
    sm, sd, st, em, ed, et = m.groups()
    # normalize times using your _format_time helper
    start_time = _format_time(st)
    end_time = _format_time(et)
    end_month = MONTHS.get(em.lower(), None)
    end_day = int(ed)
    return {"start_time": start_time, "end_time": end_time,
            "end_month": end_month, "end_day": end_day}


def _add_hours(time_str: str, hours: int = 1) -> str:
    t = (time_str or "").strip()
    if not t:
        return ""
    # support "11 AM" and "11:00 AM"
    for fmt in ("%I:%M %p", "%I %p"):
        try:
            dt = datetime.strptime(t.replace(".", ""), fmt)
            dt2 = dt + timedelta(hours=hours)
            # keep minutes only if they existed in input
            return dt2.strftime("%-I:%M %p") if ":" in t else dt2.strftime("%-I %p")
        except ValueError:
            continue
    return t  # fallback unchanged if parsing fails

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

def export_events_to_csv(library="vbpl", return_df=False):
    config = get_library_config(library)
    constants = LIBRARY_CONSTANTS.get(library, {})
    name_suffix_map = constants.get("name_suffix_map", {})
    suffix = config.get("event_name_suffix", "")

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

    # 🔧 Convert all columns to string safely
    for col in df.columns:
        df[col] = df[col].astype(str)

    original_row_count = len(df)

    required_columns = [
        "Event Name", "Location", "Categories", "Program Type", "Series", "Event Description",
        "Event Link", "Month", "Day", "Year", "Event End Date", "Site Sync Status",
        "Venue", "EVENT START DATE", "EVENT START TIME", "EVENT END DATE", "EVENT END TIME", "ALL DAY EVENT"
    ]
    for col in required_columns:
        if col not in df.columns:
            print(f"🔨 Creating missing column: {col}")
            df[col] = ""
        else:
            df[col] = df[col].fillna("").astype(str)
            

    print("\n🔎 Column counts before filtering:")
    for col in [
        "Event Name", "Venue", "EVENT START DATE", "EVENT START TIME", "EVENT END DATE",
        "EVENT END TIME", "ALL DAY EVENT", "Categories", "Event Link", "Event Description"
    ]:
        print(f"{col}: {len(df[col])}" if col in df.columns else f"❌ Missing column: {col}")
    
    # ✅ These lines must be OUTSIDE the loop above
    for col in df.columns:
        df[col] = df[col].astype(str)
    
    # 🧪 DEBUG BLOCK
    print("\n🔬 Dtypes snapshot before filtering:")
    print(df.dtypes)
    
    print("\n🔍 Any non-strings in 'Event Name'?")
    print(df[~df["Event Name"].apply(lambda x: isinstance(x, str))])
    
    # ✅ Filter and exclude
    df = df[df["Site Sync Status"].fillna("").str.strip().str.lower() == "new"]
    df = df[~df["Event Name"].str.lower().str.contains("artist of the month")]
    
    if df.empty:
        print("🚫  No new events to export.")
        return None if return_df else ""

    # Exclude any event where the only age tag is adult-related
    df["Ages"] = df["Ages"].fillna("").astype(str)
    # Custom exclusion: skip if Ages is exactly one of these problematic combinations
    EXACT_EXCLUDE_AGES = {
        "adult", "adults", "adults 18+", "18+", "adults (18+), all ages"
    }
    
    df["Ages"] = df["Ages"].fillna("").astype(str).str.strip().str.lower()
    df = df[~df["Ages"].isin(EXACT_EXCLUDE_AGES)]

    df["Event Status"] = df["Event Status"].fillna("").astype(str)
    df = df[~df["Event Status"].str.strip().str.lower().eq("cancelled")]

    # ✅ Add another short-circuit here
    if df.empty:
        print("🚫  No new events to export (after age filters).")
        return None if return_df else ""
    # 🔎 Debug: Check for non-string issues in Categories
    print("Categories type preview:")
    print(df["Categories"].apply(lambda x: f"{type(x)} - {x}" if pd.notnull(x) else "None").head(10))
    
    # ✅ Enforce type before using .str.contains
    df["Program Type"] = df["Program Type"].fillna("").astype(str)
    df["Categories"] = df["Categories"].fillna("").astype(str)
    
    df = df[~df["Program Type"].str.contains("Classes & Workshops", case=False)]
    df = df[~df["Categories"].str.contains("Classes & Workshops", case=False)]

    time_info = df["Time"].astype(str).apply(_split_times)
    time_df = pd.DataFrame(time_info.tolist(), index=df.index, columns=["start", "end", "all_day"])
    df[["EVENT START TIME", "EVENT END TIME"]] = time_df[["start", "end"]]
    df["ALL DAY EVENT"] = time_df["all_day"]
    df.loc[df["ALL DAY EVENT"] == "TRUE", ["EVENT START TIME", "EVENT END TIME"]] = ["", ""]

    # --- Handle strings like "September 6 at 9:00 am - September 7 at 6:00 pm"
    mask_datey = df["Time"].astype(str).str.contains(r'(?i)\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d+\s+at\s+\d', regex=True)
    
    def _fix_row_with_dates(row):
        parsed = _parse_time_with_dates(row["Time"])
        if not parsed:
            return row
        # override times
        row["EVENT START TIME"] = parsed["start_time"]
        row["EVENT END TIME"]   = parsed["end_time"]
        # set proper end date using the same year as the row
        try:
            year = int(str(row.get("Year", "")).strip() or str(row.get("EVENT START DATE", "")).split("-")[0])
        except Exception:
            # fallback: use year from EVENT START DATE if present
            try:
                year = int(str(row.get("EVENT START DATE", "")).split("-")[0])
            except Exception:
                year = None
        if parsed["end_month"] and year:
            end_dt = datetime(year, parsed["end_month"], parsed["end_day"])
            row["EVENT END DATE"] = end_dt.strftime("%Y-%m-%d")
        return row
    
    df = df.apply(lambda r: _fix_row_with_dates(r) if mask_datey.loc[r.name] else r, axis=1)


    # --- Custom duration fix: Gibraltar tour is a 1-hour tour (don’t use the "11-3" range)
    GIB_KEY = "gibraltar of the chesapeake and the building of a nation"
    mask = df["Event Name"].astype(str).str.lower().str.contains(GIB_KEY, na=False)
    
    # End time = start time + 1 hour (only when we have a start time)
    df.loc[mask, "EVENT END TIME"] = df.loc[mask, "EVENT START TIME"].apply(lambda t: _add_hours(t, 1))
    # Ensure it's not treated as an all-day event
    df.loc[mask, "ALL DAY EVENT"] = "FALSE"


    df["Month"] = df["Month"].astype(str)
    df["Day"] = df["Day"].astype(str)
    df["Year"] = df["Year"].astype(str)
    
    month_str = df["Month"] + " " + df["Day"] + " " + df["Year"]
    
    df["EVENT START DATE"] = pd.to_datetime(month_str, format="%b %d %Y", errors="raise").dt.strftime("%Y-%m-%d")
    df["EVENT END DATE"] = df["Event End Date"].fillna("").astype(str)
    df.loc[df["EVENT END DATE"].str.strip() == "", "EVENT END DATE"] = df["EVENT START DATE"]
    df["EVENT END DATE"] = df["EVENT END DATE"].fillna("").astype(str)

    df["Location"] = df.apply(
        lambda row: infer_location_from_title(row["Event Name"], name_suffix_map)
        if not str(row["Location"]).strip() else row["Location"], axis=1
    )

    venue_map = constants.get("venue_names") or name_suffix_map  # keep existing line

    if library == "visithampton":
        # Case/spacing-normalized mapping with fallback to original Location
        raw_loc = df["Location"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
        vm_lower = {str(k).lower(): v for k, v in (constants.get("venue_names") or {}).items()}
        df["Venue"] = raw_loc.apply(lambda x: vm_lower.get(x.lower(), x))
    else:
        df["Venue"] = (
            df["Location"]
              .str.replace(r"^Library Branch:", "", regex=True)
              .str.strip()
              .map(venue_map)
              .fillna(df["Location"].str.replace(r"^Library Branch:", "", regex=True).str.strip())
        )
        # Keep the non-visithampton filter
        invalid_venue_mask = ~df["Venue"].isin((venue_map or {}).values())
        if invalid_venue_mask.any():
            print("⚠️ Skipping events due to invalid or unmapped venue names:")
            print(df.loc[invalid_venue_mask, ["Event Name", "Venue"]])
            df = df[~invalid_venue_mask]

    def format_event_title(row):
        title = str(row.get("Event Name", "")).strip()
        # Avoid double suffix for Visithampton: keep title as-is if it already ends with the suffix
        if library == "visithampton":
            suff = (suffix or "").strip()
            if suff and title.lower().endswith(suff.lower()):
                return title
            return f"{title}{suffix}"
    
        # Others: strip " at …" then add mapped suffix (unchanged behavior)
        base = re.sub(r"\s+at\s+.*", "", title).strip()
        loc = str(row.get("Location", "")).strip()
        loc_clean = re.sub(r"^Library Branch:", "", loc).strip()
        suffix_name = name_suffix_map.get(loc_clean, loc_clean)
        out = f"{base} at {suffix_name}{suffix}" if suffix_name else base + suffix
        return str(out)
    
    # assign back safely
    titles = df.apply(format_event_title, axis=1)
    if hasattr(titles, "columns"):  # just in case
        titles = titles.iloc[:, 0]
    df["Event Name"] = titles.astype(str).values


    expected_export_cols = [
        "Event Name", "Venue", "EVENT START DATE", "EVENT START TIME", "EVENT END DATE",
        "EVENT END TIME", "ALL DAY EVENT", "Categories", "Event Link", "Event Description"
    ]
    for col in expected_export_cols:
        if col not in df.columns:
            df[col] = ""
        else:
            df[col] = df[col].fillna("").astype(str)

    print("\n🔍 Final export column lengths:")
    for col in expected_export_cols:
        print(f"{col}: {len(df[col])}")

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
    for col in str_cols:
        export_df[col] = export_df[col].map(_ascii_normalize).map(_ascii_quotes)


    csv_path = f"events_for_upload_{library}.csv"
    export_df.to_csv(csv_path, index=False)
    print(f"✅ Exported {len(export_df)} events to CSV (from {original_row_count} original rows)")

    send_notification_email_with_attachment(csv_path, config["email_subject"], config["email_recipient"])

    # ✅ Mark exported rows as "on site" in the sheet
    site_sync_col = df.columns.get_loc("Site Sync Status")
    values = sheet.get_all_values()

    # Build a map from Event Link → Sheet Row Number
    link_col_idx = df.columns.get_loc("Event Link")
    event_link_to_row = {}

    for i, row in enumerate(values[1:], start=2):  # Skip header
        if len(row) > link_col_idx:
            link = row[link_col_idx].strip()
            if link:
                event_link_to_row[link] = i

    # Prepare batch updates
    updates = []
    for link in df["Event Link"]:
        link = str(link).strip()
        row_num = event_link_to_row.get(link)

        if row_num:
            cell = rowcol_to_a1(row_num, site_sync_col + 1)
            updates.append({"range": cell, "values": [["on site"]]})

    # Perform batch update
    if updates:
        sheet.batch_update([{"range": u["range"], "values": u["values"]} for u in updates])

    if return_df:
        return export_df
    return csv_path

if __name__ == "__main__":
    LIBRARIES = ["vbpl", "npl", "chpl", "nnpl", "hpl", "ppl", "spl", "vbpr", "visithampton", "visitchesapeake"]
    print("🧪 Running unified CSV export for LIBRARIES:", LIBRARIES)

    all_exports = []
    for lib in LIBRARIES:
        print(f"🚀 Exporting {lib} …")
        df = export_events_to_csv(lib, return_df=True)
        if df is not None and not df.empty:
            all_exports.append(df)

    if all_exports:
        master_df = pd.concat(all_exports, ignore_index=True)
        csv_path = "combined_events_export.csv"
        master_df.to_csv(csv_path, index=False)
        print(f"✅ Wrote combined CSV with {len(master_df)} events")

        subject = "Unified Events Export"
        recipient = os.environ.get("EXPORT_RECIPIENT", "knowzek@gmail.com")
        send_notification_email_with_attachment(csv_path, subject, recipient)
    else:
        print("🚫 No events to export across all libraries.")


