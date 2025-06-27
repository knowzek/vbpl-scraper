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

    elif library == "chpl":
    return {
        "spreadsheet_name": "Chesapeake Library Events",
        "worksheet_name": "CHPL Events",
        "log_worksheet_name": "CHPL Log",
        "organizer_name": "Chesapeake Public Library",
        "event_name_suffix": " (Chesapeake)",
        "drive_folder_id": "13A2WzqeiOnLh7HfkHtrvT3daIStkFaFs",
        "email_recipient": "knowzek@gmail.com",
        "email_subject": "New CHPL CSV export ready"
    }

    elif library == "hpl":
    return {
        "spreadsheet_name": "Hampton Library Events",
        "worksheet_name": "HPL Events",
        "log_worksheet_name": "HPL Log",
        "organizer_name": "Hampton Public Library",
        "event_name_suffix": " (Hampton)",
        "drive_folder_id": "1brVcd-o3K1iQnPeNtUXG0hJ5LK-U_ufk",
        "email_recipient": "knowzek@gmail.com",
        "email_subject": "New HPL CSV export ready"
    }

    elif library == "nnpl":
    return {
        "spreadsheet_name": "Newport News Library Events",
        "worksheet_name": "NNPL Events",
        "log_worksheet_name": "NNPL Log",
        "organizer_name": "Newport News Public Library",
        "event_name_suffix": " (Newport News)",
        "drive_folder_id": "1cgOdSy3rPpp6l48LYPyBDqO3X-gU-gAV",
        "email_recipient": "knowzek@gmail.com",
        "email_subject": "New NNPL CSV export ready"
    }

    elif library == "spl":
    return {
        "spreadsheet_name": "Suffolk Library Events",
        "worksheet_name": "SPL Events",
        "log_worksheet_name": "SPL Log",
        "organizer_name": "Suffolk Public Library",
        "event_name_suffix": " (Suffolk)",
        "drive_folder_id": "16aBR37DboG2b84MPj0BnDJdQ833_Grta",
        "email_recipient": "knowzek@gmail.com",
        "email_subject": "New SPL CSV export ready"
    }

    elif library == "ppl":
    return {
        "spreadsheet_name": "Portsmouth Library Events",
        "worksheet_name": "PPL Events",
        "log_worksheet_name": "PPL Log",
        "organizer_name": "Portsmouth Public Library",
        "event_name_suffix": " (Portsmouth)",
        "drive_folder_id": "1glmDifkfU13PXGJN_8-sg6jfkZUJWxFq",
        "email_recipient": "knowzek@gmail.com",
        "email_subject": "New PPL CSV export ready"
    }
    
    else:
        raise ValueError(f"Unsupported library code: {library}")
