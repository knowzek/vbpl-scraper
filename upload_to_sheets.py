from datetime import datetime
import os
import gspread
from google.oauth2 import service_account
import traceback
from config import get_library_config
import json
import re
from constants import LIBRARY_CONSTANTS, TITLE_KEYWORD_TO_CATEGORY, UNWANTED_TITLE_KEYWORDS
from constants import COMBINED_KEYWORD_TO_CATEGORY
import pandas as pd
always_on = library_constants.get("always_on_categories", [])

def has_audience_tag(tags):
    return any("Audience -" in tag for tag in tags)

def _has_unwanted_title(title: str) -> bool:
    t = (title or "").lower()
    for kw in UNWANTED_TITLE_KEYWORDS:
        # whole-word, case-insensitive match
        if re.search(rf"\b{re.escape(kw.lower())}\b", t):
            return True
    return False

TIME_OK = re.compile(r"\b\d{1,2}(:\d{2})?\s*[ap]m\b", re.I)

def _has_valid_time_str(t: str) -> bool:
    t = (t or "").strip().lower()
    if not t:
        return False
    # treat “All Day” style as valid
    if t in ("all day", "all-day", "all day event", "all-day event"):
        return True
    # accept anything that contains at least one AM/PM time
    return bool(TIME_OK.search(t))

def _clean_link(url: str) -> str:
    cleaned = (
        url.replace("/index.php/", "/")
           .replace("/index.php", "/")
    )
    return cleaned.replace("://", ":::").replace("//", "/").replace(":::", "://")


import os, json
from google.oauth2 import service_account

def connect_to_sheet(spreadsheet_name, worksheet_name):
    creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not creds_json:
        # Fallback to Render Secret File mount
        secret_path = "/etc/secrets/GOOGLE_APPLICATION_CREDENTIALS_JSON"
        if os.path.exists(secret_path):
            with open(secret_path, "r") as f:
                creds_json = f.read()

    if not creds_json:
        raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS_JSON env var not set")

    creds_dict = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    client = gspread.authorize(creds)
    return client.open(spreadsheet_name).worksheet(worksheet_name)

def normalize(row):
    return [cell.strip() for cell in row[:13]] + [""] * (13 - len(row))

def _kw_hit(text: str, kw: str) -> bool:
    t = (text or "").lower()
    k = (kw or "").lower()
    # match kw as a whole word/phrase (no letter/number touching it)
    return re.search(rf'(?<!\w){re.escape(k)}(?!\w)', t) is not None

def upload_events_to_sheet(events, sheet=None, mode="full", library="vbpl", age_to_categories={}, name_suffix_map={}):
    config = get_library_config(library)
    SPREADSHEET_NAME = config["spreadsheet_name"]
    WORKSHEET_NAME = config["worksheet_name"]
    LOG_WORKSHEET_NAME = config["log_worksheet_name"]
    library_constants = LIBRARY_CONSTANTS.get(library, {})
    program_type_to_categories = library_constants.get("program_type_to_categories", {})
    venue_names_map_lc = {k.lower(): v for k, v in library_constants.get("venue_names", {}).items()}
    age_to_categories = age_to_categories or library_constants.get("age_to_categories", {})
    name_suffix_map = name_suffix_map or library_constants.get("name_suffix_map", {})


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

                title_for_filter = (event.get("Event Name", "") or "").strip()
                if _has_unwanted_title(title_for_filter):
                    print(f"⏭️ Skipping (unwanted title): {title_for_filter}")
                    skipped += 1
                    continue

                # === Exclude unwanted events for specific scrapers ===
                if library in ["visitsuffolk", "portsvaevents", "visitnewportnews", "visithampton", "visitchesapeake"]:
                    exclude_keywords = ["live", "patio"]
                    name_text = (event.get("Event Name", "") or "").lower()
                    desc_text = (event.get("Event Description", "") or "").lower()
                    if any(kw in name_text for kw in exclude_keywords) or any(kw in desc_text for kw in exclude_keywords):
                        print(f"⏭️ Skipping (excluded keyword): {event.get('Event Name')}")
                        skipped += 1
                        continue
                
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                program_type = event.get("Program Type", "")
                # Ensure categories always exists (prevents UnboundLocalError)
                categories = ""

                if library == "ppl":
                    # Instead of using only precomputed tags, apply full logic
                    categories = ""

                # --- YPL pre-filtering and normalization ---
                if library == "ypl":
                    event["Location"] = event.get("Location", "").strip()
                
                    # (3) Exclude if Ages is ONLY adult
                    ages_only = re.sub(r"\s+", " ", (event.get("Ages", "") or "").strip().lower()).strip(", ")
                    if ages_only in {"adult", "adults", "adults 18+", "18+"}:
                        print(f"⏭️ Skipping YPL adult-only event: {event.get('Event Name')}")
                        skipped += 1
                        continue

                elif library == "hpl":
                    program_types = [pt.strip().lower() for pt in program_type.split(",") if pt.strip()]
                    matched_tags = []
                    for pt in program_types:
                        cat = program_type_to_categories.get(pt)
                        if cat:
                            matched_tags.extend([c.strip() for c in cat.split(",")])
                    categories = ", ".join(dict.fromkeys(matched_tags))  # remove duplicates, preserve order
                
                elif library in ("vbpr", "visithampton", "visitchesapeake", "visitnewportnews", "portsvaevents", "visitsuffolk", "visitnorfolk"):
                    # For VBPR, use the categories provided by the scraper
                    categories = event.get("Categories", "").strip()
                else:
                    # Default fallback for all other libraries
                    categories = program_type_to_categories.get(program_type, "")


                if library == "chpl" and age_to_categories:
                    audience_keys = [a.strip() for a in event.get("Ages", "").split(",") if a.strip()]
                    all_tags = []
                    for tag in audience_keys:
                        tags = age_to_categories.get(tag)
                        if tags:
                            all_tags.extend([t.strip() for t in tags.split(",")])
                    if all_tags:
                        categories = ", ".join(dict.fromkeys(all_tags))

                ages_raw = event.get("Ages", "")
                age_tags = []
                nums = [int(n) for n in re.findall(r"\d+", ages_raw) if int(n) > 0]

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
                    if min_age >= 13:
                        age_tags.append("Audience - Teens")

                # Age-based category tags
                audience_keys = [a.strip() for a in ages_raw.split(",") if a.strip()]
                all_tags = []
                
                if age_to_categories:
                    for tag in audience_keys:
                        tags = age_to_categories.get(tag)
                        if tags:
                            all_tags.extend([t.strip() for t in tags.split(",")])
                
                # Only add fuzzy age tags if structured audience tags aren't already present
                if age_tags and not has_audience_tag(all_tags):
                    all_tags.extend(age_tags)

                # Ensure description exists for keyword tagging and sheet column
                desc_value = (
                    event.get("Event Description")
                    or event.get("Description")
                    or event.get("Desc")
                    or event.get("Event Details")
                    or ""
                )

                # === Normalize title and description text
                title_text = (event.get("Event Name", "") or "").lower()
                full_text = f"{event.get('Event Name', '')} {desc_value}".lower()

                title_based_tags = []
                
                # Single keywords: title OR description, with word boundaries
                for keyword, cat in TITLE_KEYWORD_TO_CATEGORY.items():
                    if _kw_hit(title_text, keyword) or _kw_hit(full_text, keyword):
                        title_based_tags.extend([c.strip() for c in cat.split(",")])
                
                # Combined keyword pairs: both must hit with word boundaries
                for (kw1, kw2), cat in COMBINED_KEYWORD_TO_CATEGORY.items():
                    if _kw_hit(full_text, kw1) and _kw_hit(full_text, kw2):
                        title_based_tags.extend([c.strip() for c in cat.split(",")])
                
                # Build the tag list from the three sources
                # 1) Start from program-type/default categories
                tag_list = [c.strip() for c in categories.split(",") if c.strip()]
                
                # 2) Add age-based categories
                tag_list.extend(all_tags)
                
                # 3) Add keyword categories
                tag_list.extend(title_based_tags)

                if always_on:
                    tag_list.extend(always_on)
                
                # YPL: always add base tags
                if library == "ypl":
                    tag_list.extend([
                        "Audience - Free Event",
                        "Event Location - Yorktown / York County",
                    ])

                # Always add base tags for NPL
                if library == "npl":
                    tag_list.extend(["Event Location - Norfolk", "Audience - Free Event"])
                
                # If nothing matched at all, add a reasonable fallback
                if not tag_list:
                    raw_location = (event.get("Location", "") or "").strip()
                    fallback_city = ""
                    for city in ("Norfolk", "Virginia Beach", "Chesapeake", "Portsmouth", "Hampton", "Newport News", "Suffolk"):
                        if city.lower() in raw_location.lower():
                            fallback_city = city
                            break
                    if library == "ypl":
                        # Always at least these for YPL
                        tag_list.extend([
                            "Audience - Free Event",
                            "Event Location - Yorktown",
                            "Event Location - York County",
                        ])
                    else:
                        tag_list.append(
                            f"Event Location - {fallback_city}, Audience - Free Event"
                            if fallback_city else
                            "Audience - Free Event"
                        )
                
                # Final dedupe to string
                categories = ", ".join(dict.fromkeys(tag_list))
                print(f"🧾 Final categories for {event.get('Event Name')}: {categories}")


                name_original = event.get("Event Name", "")
                name_without_at = re.sub(r"\s*@\s*[^@,;:\\/]+", "", name_original, flags=re.IGNORECASE).strip()
                # For visithampton: DO NOT strip " at ...".
                # For others: keep stripping anything after " at ".
                if library == "visithampton":
                    name_cleaned = name_without_at
                else:
                    name_cleaned = re.sub(r"\s+at\s+.*", "", name_without_at, flags=re.IGNORECASE).strip()
                
                # Use Venue for visithampton (fallback to Location); others use Location as before
                if library == "visithampton":
                    pref_loc = (event.get("Venue", "") or "").strip() or (event.get("Location", "") or "").strip()
                else:
                    pref_loc = (event.get("Location", "") or "").strip()
                
                suffix = config.get("event_name_suffix", "")
                loc_clean = re.sub(r"^Library Branch:", "", pref_loc).strip()
                display_loc = name_suffix_map.get(loc_clean, loc_clean)
                
                # Normalize casing for suffix checks
                base_name = name_cleaned.lower()
                loc_lower = display_loc.lower()
                suffix_lower = (suffix or "").lower()

                # Avoid duplicate location suffix
                if base_name.endswith(loc_lower) or suffix_lower in base_name:
                    event_name = f"{name_cleaned}"
                else:
                    event_name = f"{name_cleaned} at {display_loc}"
                
                # Append suffix only if not already present
                if suffix and suffix not in event_name:
                    event_name += suffix

                if not categories:
                    categories = event.get("Categories", "") or f"Event Location - {config['organizer_name']}, Audience - Free Event, Audience - Family Event"


                # Decide what to put in the Google Sheet "Location" (Column F)
                organizer = (event.get("Organizer", "") or "").strip().lower()
                if library == "visithampton" and organizer == "fort monroe national monument":
                    sheet_location = "Fort Monroe Visitor & Education Center"
                elif library == "visithampton":
                    sheet_location = (event.get("Venue", "") or "").strip()
                else:
                    sheet_location = (event.get("Location", "") or "").strip()

                # Normalize Location via constants.py venue_names (case-insensitive)
                loc_key = re.sub(r"^Library Branch:", "", sheet_location).strip()
                sheet_location = venue_names_map_lc.get(loc_key.lower(), loc_key)

                row_core = [
                    event_name,
                    link,
                    event.get("Event Status", ""),
                    event.get("Time", ""),
                    event.get("Ages", ""),
                    sheet_location,
                    event.get("Month", ""),
                    event.get("Day", ""),
                    event.get("Year", ""),
                    desc_value,
                    event.get("Series", ""),
                    program_type,
                    categories
                ]
                print("🧾 Raw row_core before normalize:", row_core)
                new_core = normalize(row_core)
                existing_row = existing_data.get(link, [""] * 16)
                existing_core = normalize(existing_row)

                # --- Needs-Attention logic ---
                time_str = (event.get("Time") or "").strip()
                title    = (event.get("Event Name") or "")
                
                needs_attention = (
                    not (desc_value or "").strip() or              # missing description
                    not (sheet_location or "").strip() or          # missing location
                    not _has_valid_time_str(time_str) or           # missing/invalid time
                    ("exhibit" in title.lower())                   # exhibit keyword
                )
                
                if needs_attention:
                    site_sync_status = "NEEDS ATTENTION"
                    status = "review needed"   # keep if you want this reflected in the Status column
                else:
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
                    print("🔍 New row to append:", full_row)
                    new_rows.append(full_row)
                    added += 1
    
                elif new_core != existing_core:
                    print(f"🔄 Updated row {link_to_row_index[link]}:", full_row)
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

        # Export REVIEW NEEDED rows to CSV
        review_rows = [r for r in new_rows if "REVIEW NEEDED" in r[-1]]
#       if review_rows:
#           review_df = pd.DataFrame(review_rows, columns=headers[:len(review_rows[0])])
#           review_path = f"Review Needed - Missing Info - {library}.csv"
#           review_df.to_csv(review_path, index=False)
#           print(f"📎 Exported {len(review_rows)} flagged rows to {review_path}")
#
#            send_notification_email_with_attachment(
#            review_path,
#            f"{library.upper()} — Review Needed: Missing Info",
#            config["email_recipient"]
#           )


        if new_rows:
            print("🔍 Full row to upload:", full_row)
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

def export_all_events_to_csv_and_email():
    LIBRARIES = [
        "vbpl",
        "npl",
        "chpl",
        "nnpl",
        "hpl",
        "spl",
        "ppl",
        "visithampton",
        "visitchesapeake",
        "visitnewportnews",
        "portsvaevents",
        "visitsuffolk"
    ]
    all_rows = []
    for lib in LIBRARIES:
        print(f"📥 Fetching events from: {lib.upper()}")
        config = get_library_config(lib)
        creds = service_account.Credentials.from_service_account_file(
            "/etc/secrets/GOOGLE_APPLICATION_CREDENTIALS_JSON",
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        client = gspread.authorize(creds)
        sheet = client.open(config["spreadsheet_name"]).worksheet(config["worksheet_name"])
        rows = sheet.get_all_values()
        if not all_rows:
            all_rows.append(rows[0])  # headers once
        all_rows.extend(rows[1:])     # all events

    # Write to CSV
    df = pd.DataFrame(all_rows[1:], columns=all_rows[0])
    export_path = "All_Libraries_Events.csv"
    df.to_csv(export_path, index=False)
    print(f"✅ Exported {len(df)} rows to {export_path}")

    # Email it
    from export_to_csv import send_notification_email_with_attachment
    send_notification_email_with_attachment(
        export_path,
        "All Libraries – Events Export",
        os.environ.get("EVENT_EXPORT_RECIPIENT") or "your@email.com"
    )

if __name__ == "__main__":
    export_all_events_to_csv_and_email()


