def get_library_config(library):
    if library == "vbpl":
        return {
            "spreadsheet_name": "Virginia Beach Library Events",
            "worksheet_name": "VBPL Events",
            "log_worksheet_name": "VBPL Log",
            "organizer_name": "Virginia Beach Public Library",
            "event_name_suffix": " (Virginia Beach)",
            "drive_folder_id": "16pkTscctVQgywEU8mkHeqE3JS55dnlrz",
            "email_recipient": "knowzek@gmail.com",
            "email_subject": "New VBPL CSV export ready"
        }
    elif library == "npl":
        return {
            "spreadsheet_name": "Norfolk Library Events",
            "worksheet_name": "NPL Events",
            "log_worksheet_name": "NPL Log",
            "organizer_name": "Norfolk Public Library",
            "event_name_suffix": " (Norfolk)",
            "drive_folder_id": "1pr1xTMnxE9rAkhmG6YxnSkZGWb_7vkpn",
            "email_recipient": "knowzek@gmail.com",
            "email_subject": "New NPL CSV export ready"
        }
    else:
        raise ValueError(f"Unsupported library code: {library}")
