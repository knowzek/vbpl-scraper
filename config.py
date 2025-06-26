def get_library_config(library):
    """Return config dict for given library code."""
    if library == "vbpl":
        return {
            "spreadsheet_name": "Virginia Beach Library Events",
            "worksheet_name": "VBPL Events",
            "log_worksheet_name": "VBPL Log",
            "organizer_name": "Virginia Beach Public Library",
            "event_name_suffix": " (Virginia Beach)",
        }
    elif library == "npl":
        return {
            "spreadsheet_name": "Norfolk Library Events",
            "worksheet_name": "NPL Events",
            "log_worksheet_name": "NPL Log",
            "organizer_name": "Norfolk Public Library",
            "event_name_suffix": " (Norfolk)",
        }
    else:
        raise ValueError(f"Unsupported library code: {library}")
