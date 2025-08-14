import json, requests, os
import re
from typing import Dict, Optional
from datetime import datetime, timedelta

# helpers.py
import re
from datetime import datetime, timedelta

TIME12_RE = re.compile(r'\b(1[0-2]|0?[1-9])(?::([0-5]\d))?\s*([ap]\.?m\.?)\b', re.I)

def _fmt12(dt):  # always "H:MM AM/PM"
    s = dt.strftime("%I:%M %p")
    return s.lstrip("0")  # drop leading zero for 01..09

def _parse12(h, m, ap):
    h = int(h)
    m = int(m or 0)
    ap = ap.lower()
    if ap.startswith('p') and h != 12: h += 12
    if ap.startswith('a') and h == 12: h = 0
    return datetime(2000, 1, 1, h, m)

def normalize_time_string(raw: str, default_minutes=60) -> str:
    """Return 'H:MM AM - H:MM PM', 'All Day Event', or original if unparseable/multi-schedule."""
    if not raw:
        return ""
    s = raw.strip()

    # Standardize separators first
    s = re.sub(r'\bto\b', '-', s, flags=re.I)         # "7 PM to 9 PM" -> "7 PM - 9 PM"
    s = re.sub(r'\s*[-–—]\s*', ' - ', s)              # normalize any dash spacing
    s = re.sub(r':([0-5]\d):[0-5]\d\b', r':\1', s)    # strip trailing seconds in any times

    # All-day?
    if re.search(r'\ball\s*day\b', s, re.I):
        return "All Day Event"

    # Extract 12h clock times anywhere in the string
    matches = list(TIME12_RE.findall(s))

    # If this looks like an hours-of-operation string (>=3 times), don't guess — keep original
    if len(matches) >= 3:
        return s

    if not matches:
        return s

    start_dt = _parse12(*matches[0])
    if len(matches) >= 2:
        end_dt = _parse12(*matches[-1])
    else:
        end_dt = start_dt + timedelta(minutes=default_minutes)

    return f"{_fmt12(start_dt)} - {_fmt12(end_dt)}"


def wJson(jsonFile, filePath):
    with open(filePath, 'w', encoding='utf-8') as jsonWriter:
        json.dump(jsonFile, jsonWriter, ensure_ascii=False, indent=4)

def rJson(filePath):
    with open(filePath, encoding='utf-8') as jsonReader:
        return json.load(jsonReader)
    
def newFolderCreate(folder_name,dPath):
    complete_path = os.path.join(dPath, folder_name)
    if not (os.path.exists(complete_path) and os.path.isdir(complete_path)):
        new_directory = os.path.join(dPath, folder_name)
        os.makedirs(new_directory)


# Buckets → tags
_AGE_BUCKETS = [
    (0, 2,  "Audience - Parent & Me, Audience - Toddler/Infant"),
    (3, 4,  "Audience - Preschool Age"),
    (5, 12, "Audience - School Age"),
    (13, 18, "Audience - Teens"),
]

def infer_age_categories_from_description(description: str) -> Dict[str, Optional[str]]:
    """
    Parse a description for phrases like:
      - "for ages 7 and up", "ages 7+", "age 7+"
      - "for ages 2-4", "ages 2 to 4", "ages 2–4", "ages 2 through 4"
      - "for ages 3" (single age)
    Returns:
      {
        "min_age": int|None,
        "max_age": int|None,
        "categories": str  # comma-separated audience tags
      }
    If nothing is found, min/max are None and categories is "".
    """
    if not description:
        return {"min_age": None, "max_age": None, "categories": ""}

    txt = " ".join(description.lower().split())
    txt = txt.replace("–", "-").replace("—", "-")  # normalize dashes

    min_age = max_age = None

    # Case A: "ages 7 and up" / "age 7+" / "ages 7+"
    m = re.search(r"(?:for\s+)?ages?\s*(\d{1,2})\s*(?:\+|and\s+up)\b", txt)
    if m:
        min_age = int(m.group(1))
        max_age = 18

    # Case B: "ages 2-4" / "ages 2 to 4" / "ages 2 through 4"
    if min_age is None:
        m = re.search(r"(?:for\s+)?ages?\s*(\d{1,2})\s*(?:-|to|through)\s*(\d{1,2})\b", txt)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            min_age, max_age = (a, b) if a <= b else (b, a)

    # Case C: single age "for ages 3" / "age 3"
    if min_age is None:
        m = re.search(r"(?:for\s+)?ages?\s*(\d{1,2})\b(?!\s*(?:\+|and\s+up|-|to|through))", txt)
        if m:
            min_age = max_age = int(m.group(1))

    if min_age is None:
        return {"min_age": None, "max_age": None, "categories": ""}

    # Clamp to 0..18 and build overlapping bucket tags
    min_age = max(0, min_age)
    max_age = min(18, max_age if max_age is not None else min_age)

    tags = []
    for lo, hi, tag_str in _AGE_BUCKETS:
        # include if the [min_age, max_age] overlaps this bucket
        if not (max_age < lo or min_age > hi):
            tags.extend([t.strip() for t in tag_str.split(",") if t.strip()])

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for t in tags:
        tl = t.lower()
        if tl not in seen:
            seen.add(tl)
            deduped.append(t)

    return {"min_age": min_age, "max_age": max_age, "categories": ", ".join(deduped)}
