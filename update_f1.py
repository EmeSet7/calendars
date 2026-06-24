import requests
from datetime import datetime, timezone

OPENF1_BASE = "https://api.openf1.org/v1"
ICS_FILE = "F1.ics"


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


def get_sessions(year):
    """Return every session (practice, qualifying, sprint, race) for the season."""
    response = requests.get(f"{OPENF1_BASE}/sessions", params={"year": year})
    response.raise_for_status()
    return response.json()


def short_gp_name(meeting_name):
    """'Australian Grand Prix' -> 'Australian GP'"""
    return meeting_name.replace(" Grand Prix", " GP")


def session_emoji(session_name):
    name = session_name.lower()
    if "practice" in name:
        return "🔧"
    if "sprint" in name:
        return "⚡"
    if "qualifying" in name:
        return "📍"
    return "🏁"  # Race


def escape_ics_text(text):
    """Escape characters with special meaning in ICS text fields."""
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def format_utc(iso_string):
    """Convert an API timestamp like '2026-03-06T03:00:00+00:00' to ICS UTC format."""
    dt = datetime.fromisoformat(iso_string)
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def build_event(session, meeting):
    emoji = session_emoji(session["session_name"])
    gp_name = short_gp_name(meeting["meeting_name"])
    summary = f"{emoji} F1 R{meeting['round']} — {gp_name} · {session['session_name']}"

    description = (
        f"Round {meeting['round']} · {session['session_name']}\n"
        f"Circuit: {meeting.get('circuit_short_name', '')}"
    )
    location = f"{meeting.get('circuit_short_name', '')}, {meeting.get('location', '')}, {meeting.get('country_name', '')}"

    return "\n".join([
        "BEGIN:VEVENT",
        f"UID:f1-{session['session_key']}@tiago",
        f"DTSTART:{format_utc(session['date_start'])}",
        f"DTEND:{format_utc(session['date_end'])}",
        f"SUMMARY:{escape_ics_text(summary)}",
        f"DESCRIPTION:{escape_ics_text(description)}",
        f"LOCATION:{escape_ics_text(location)}",
        "END:VEVENT",
    ])


def build_calendar(meetings, sessions):
    meetings_by_key = {m["meeting_key"]: m for m in meetings}

    events = []
    for session in sessions:
        if session.get("is_cancelled"):
            continue
        meeting = meetings_by_key.get(session["meeting_key"])
        if not meeting:
            continue
        events.append(build_event(session, meeting))

    header = "\n".join([
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Tiago Cardoso//F1 Calendar Auto-Update//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Formula 1",
    ])
    footer = "END:VCALENDAR"

    return "\n\n".join([header] + events + [footer]) + "\n"


def main():
    year = get_season_year()
    print(f"Fetching {year} F1 season schedule...")

    meetings = get_meetings(year)
    if not meetings:
        print(f"No meetings found for {year} yet. Leaving existing calendar untouched.")
        return

    sessions = get_sessions(year)
    print(f"Found {len(meetings)} GP weekends and {len(sessions)} sessions.")

    calendar_text = build_calendar(meetings, sessions)

    with open(ICS_FILE, "w", encoding="utf-8") as f:
        f.write(calendar_text)

    print(f"Wrote {ICS_FILE}")


if __name__ == "__main__":
    main()
