import requests
import re
from datetime import datetime, timezone

ICS_FILE = "f12026.ics"
OPENF1_BASE = "https://api.openf1.org/v1"

def get_latest_session():
    """Get the most recent race session."""
    r = requests.get(f"{OPENF1_BASE}/sessions", params={
        "year": 2026,
        "session_name": "Race",
    })
    sessions = r.json()
    if not sessions:
        return None
    # Filter past sessions only
    now = datetime.now(timezone.utc)
    past = [s for s in sessions if datetime.fromisoformat(s["date_end"].replace("Z", "+00:00")) < now]
    if not past:
        return None
    return sorted(past, key=lambda s: s["date_end"])[-1]

def get_podium(session_key):
    """Get top 3 finishers for a session."""
    r = requests.get(f"{OPENF1_BASE}/position", params={
        "session_key": session_key,
        "position<=": 3,
    })
    positions = r.json()
    # Get final position for each driver (last entry per driver)
    by_driver = {}
    for p in positions:
        by_driver[p["driver_number"]] = p
    top3 = sorted([p for p in by_driver.values() if p["position"] <= 3], key=lambda x: x["position"])

    podium = []
    for p in top3:
        driver_r = requests.get(f"{OPENF1_BASE}/drivers", params={
            "session_key": session_key,
            "driver_number": p["driver_number"],
        })
        drivers = driver_r.json()
        if drivers:
            d = drivers[0]
            podium.append({
                "position": p["position"],
                "name": d.get("full_name", "Unknown"),
                "team": d.get("team_name", ""),
            })
    return podium

def update_ics(session, podium):
    """Update the race event in the ICS file with podium results."""
    if not podium:
        print("No podium data found.")
        return

    gp_name = session.get("meeting_name", "")
    round_num = session.get("meeting_key", "")

    medals = ["🥇", "🥈", "🥉"]
    podium_text = "\\n".join(
        f"{medals[p['position']-1]} {p['name']} ({p['team']})"
        for p in podium
    )
    winner = podium[0]
    winner_short = winner["name"].split()[-1]  # Last name
    team_short = winner["team"]

    with open(ICS_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Find and update the race event summary (title) - look for matching GP name pattern
    # Match race events that don't already have a winner
    race_summary_pattern = re.compile(
        r'(SUMMARY:🏁 F1 R\d+ — ' + re.escape(gp_name) + r' GP · )(.*?)(\n)',
        re.IGNORECASE
    )

    # Update summary with winner
    new_summary = rf'\g<1>{winner_short} wins ({team_short})\3'
    content, n = re.subn(race_summary_pattern, new_summary, content)

    if n == 0:
        print(f"Could not find race event for: {gp_name}")
        return

    # Update description with podium
    desc_pattern = re.compile(
        r'(DESCRIPTION:Round \d+ · Race\\n.*?\\n)(.*?)(\\n\nLOCATION)',
        re.DOTALL
    )
    # Replace description podium block
    with open(ICS_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Updated: {gp_name} GP — Winner: {winner['name']}")

def main():
    print("Fetching latest F1 race session...")
    session = get_latest_session()
    if not session:
        print("No completed race sessions found.")
        return

    print(f"Found: {session.get('meeting_name')} GP (key: {session.get('session_key')})")

    podium = get_podium(session["session_key"])
    if not podium:
        print("Could not retrieve podium.")
        return

    print("Podium:", [(p["position"], p["name"]) for p in podium])
    update_ics(session, podium)

if __name__ == "__main__":
    main()
