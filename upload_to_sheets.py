import gspread
from oauth2client.service_account import ServiceAccountCredentials

def upload_events_to_sheet(events):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)

    sheet = client.open("Virginia Beach Library Events").worksheet("VBPL Events")

    # Get all existing event URLs
    existing_urls = set(row[1] for row in sheet.get_all_values()[1:] if len(row) > 1)

    new_rows = []
    for event in events:
        if event["Event Link"] not in existing_urls:
            new_rows.append([
                event["Event Name"],
                event["Event Link"],
                event["Event Status"],
                event["Time"],
                event["Ages"],
                event["Location"],
                event["Month"],
                event["Day"],
                event["Year"],
                event["Event Description"],
            ])

    if new_rows:
        sheet.append_rows(new_rows, value_input_option="RAW")
    else:
        print("🟡 No new events to add.")
