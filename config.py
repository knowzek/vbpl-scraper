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
        
    elif library == "vbpr":
        return {
            "spreadsheet_name": "Virginia Beach Parks & Rec Events",
            "worksheet_name": "VBPR Events",
            "log_worksheet_name": "VBPR Log",
            "organizer_name": "Virginia Beach Parks & Rec",
            "event_name_suffix": " (Virginia Beach)",
            "drive_folder_id": "1fuDkdt6MVydRKQfmyUVabVCboctCDtQ6",  # or use a new one
            "email_recipient": "knowzek@gmail.com",
            "email_subject": "New VBPR CSV export ready"
        }

    elif library == "visitchesapeake":
        return {
            "spreadsheet_name": "VisitChesapeake Events",
            "worksheet_name": "VisitChesapeake Events",
            "log_worksheet_name": "VisitChesapeake Log",
            "organizer_name": "Chesapeake Parks, Recreation, and Tourism",
            "event_name_suffix": " (Chesapeake)",
            "drive_folder_id": "1K2IrUB20XIeHm6gvl-dlZDb3NoD7Jlur",  # or use a new one
            "email_recipient": "knowzek@gmail.com",
            "email_subject": "New VisitChesapeake CSV export ready"
        }

    elif library == "visithampton":
        return {
            "spreadsheet_name": "VisitHampton Events",
            "worksheet_name": "VisitHampton Events",
            "log_worksheet_name": "VisitHampton Log",
            "organizer_name": "Visit Hampton VA",
            "event_name_suffix": " (Hampton)",
            "drive_folder_id": "1WZL7Y_CvnRd4Tr9bImjmVgeYkXI3XK90",  # or use a new one
            "email_recipient": "knowzek@gmail.com",
            "email_subject": "New VisitHampton CSV export ready"
        }
    
    
    else:
        raise ValueError(f"Unsupported library code: {library}")


def map_age_to_categories(min_age, max_age):
    from constants import AGE_RANGE_TO_CATEGORY

    matches = []

    # Treat open-ended ranges like "6+" as including up to age 17
    if max_age == 0:
        max_age = 17

    for min_ref, max_ref, category in AGE_RANGE_TO_CATEGORY:
        if (
            (min_age >= min_ref and min_age <= max_ref)
            or (max_age >= min_ref and max_age <= max_ref)
            or (min_age <= min_ref and max_age >= max_ref)  # fully contains the range
        ):
            matches.append(category)

    return ", ".join(matches)
