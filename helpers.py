import json, requests, os
import re
from typing import Dict, Optional
from datetime import datetime, timedelta


# 12h like "7", "7:30", "07:30 pm", "11AM"
TIME12_RE = re.compile(r'\b(1[0-2]|0?[1-9])(?::([0-5]\d))?\s*([ap]\.?m\.?)\b', re.I)
# 24h like "17:00" or "17:00:00"
TIME24_RE = re.compile(r'^\s*([01]?\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?\s*$')

def _fmt12(dt: datetime) -> str:
    return dt.strftime("%I:%M %p").lstrip("0")

def _parse12_to_dt(t: str) -> datetime | None:
    m = TIME12_RE.match(t.strip())
    if not m: return None
    h, mi, ap = m.groups()
    h = int(h); mi = int(mi or 0)
    if ap[0].lower() == "p" and h != 12: h += 12
    if ap[0].lower() == "a" and h == 12: h = 0
    return datetime(2000, 1, 1, h, mi)

def to_12h(s: str) -> str:
    """'17:00' → '5:00 PM', '17:00:00' → '5:00 PM', '11AM' → '11:00 AM'. Else unchanged."""
    s = (s or "").strip()
    if not s: return ""
    m = TIME24_RE.match(s)
    if m:
        h = int(m.group(1)); mi = int(m.group(2))
        ap = "AM" if h < 12 else "PM"
        h12 = 12 if h % 12 == 0 else h % 12
        return f"{h12}:{mi:02d} {ap}"
    m2 = TIME12_RE.search(s)
    if m2:
        h, mi, ap = m2.groups()
        return f"{int(h)}:{(mi or '00'):s} {'AM' if ap[0].lower()=='a' else 'PM'}"
    return s

def normalize_time_string(raw: str, default_minutes=60, keep_original_if_many_times=True) -> str:
    """
    Returns 'H:MM AM - H:MM PM', 'All Day Event', or original if unparseable/multi-schedule.
    - Converts 'to' → ' - ' and strips seconds.
    - If ≥3 times found (store hours), leaves original.
    """
    if not raw: return ""
    s = raw.strip()
    s = re.sub(r'\bto\b', '-', s, flags=re.I)
    s = re.sub(r'\s*[-–—]\s*', ' - ', s)
    s = re.sub(r':([0-5]\d):[0-5]\d\b', r':\1', s)  # drop :ss

    if re.search(r'\ball\s*day\b', s, re.I):
        return "All Day Event"

    # Find times: convert any 24h tokens to 12h first, then collect 12h.
    tokens = []
    for part in re.split(r'[^0-9apm:]+', s):
        t12 = to_12h(part)
        if TIME12_RE.match(t12):
            tokens.append(t12)

    if keep_original_if_many_times and len(tokens) >= 3:
        return s
    if not tokens:
        return s

    start = _parse12_to_dt(tokens[0])
    end = _parse12_to_dt(tokens[-1]) if len(tokens) >= 2 else (start + timedelta(minutes=default_minutes))
    return f"{_fmt12(start)} - {_fmt12(end)}"

def normalize_time_from_fields(times_text=None, start_time=None, end_time=None, default_minutes=60) -> str:
    """Single entrypoint for scrapers. Feed whatever fields you have; get a clean display string."""
    pre = (times_text or "").strip()
    pre = (pre.replace("Starting:", "").replace("starting:", "")
             .replace("From:", "").replace("from:", "").strip())
    if (not pre) and start_time:
        pre = to_12h(start_time)
    end_12 = to_12h(end_time) if end_time else ""
    s = f"{pre} - {end_12}".strip() if not end_12 else pre
    return normalize_time_string(s, default_minutes=default_minutes)

def split_display_time(display: str):
    """
    From a display string, return: (start_12, end_12, start_24, end_24, all_day_bool).
    Useful in upload_to_sheets for separate columns.
    """
    if not display: return "", "", "", "", False
    if "all day" in display.lower():
        return "", "", "", "", True
    if " - " not in display:
        return "", "", "", "", False
    left, right = [x.strip() for x in display.split(" - ", 1)]
    m1 = TIME12_RE.match(left); m2 = TIME12_RE.match(right)
    def _to24(m):
        if not m: return ""
        h, mi, ap = m.groups()
        h = int(h); mi = int(mi or 0)
        if ap[0].lower()=='p' and h != 12: h += 12
        if ap[0].lower()=='a' and h == 12: h = 0
        return f"{h:02d}:{mi:02d}"
    return left, right, _to24(m1), _to24(m2), False



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


if __name__ == "__main__":
    pass