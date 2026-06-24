import requests
from datetime import datetime, timezone

ICS_FILE = "f12026.ics"
OPENF1_BASE = "https://api.openf1.org/v1"

def get_season_year():
    """Use the current calendar year, so this keeps working without manual updates each season."""
    return datetime.now(timezone.utc).year

def get_meetings(year):
    """Return all real Grand Prix weekends for the season (pre-season testing excluded),
    sorted chronologically, with round numbers attached."""
    response = requests.get(f"{OPENF1_BASE}/meetings", params={"year": year})
    response.raise_for_status()
    meetings = response.json()

    meetings = [m for m in meetings if "test" not in m["meeting_name"].lower()]
    meetings.sort(key=lambda m: m["date_start"])
    for i, m in enumerate(meetings, start=1):
        m["round"] = i

    return meetings

print(get_season_year())
print(get_meetings(2026))


