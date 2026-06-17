import requests
import re
from datetime import datetime, timezone

ICS_FILE = "f12026.ics"
BASE = "https://api.openf1.org/v1"

def get(endpoint, params={}):
    r = requests.get(f"{BASE}/{endpoint}", params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def get_latest_race_session():
    sessions = get("sessions", {"year": 2026, "session_name": "Race"})
    now = datetime.now(timezone.utc)
    past = [
        s for s in sessions
        if s.get("date_end") and
        datetime.fromisoformat(s["date_end"].replace("Z", "+00:00")) < now
    ]
    if not past:
        return None
    return sorted(past, key=lambda s: s["date_end"])[-1]

def get_podium(session_key):
    # Get final positions - take last recorded position per driver
    positions = get("position", {"session_key": session_key})
    if not positions or not isinstance(positions[0], dict):
        print("Unexpected position data format")
        return []

    # Keep last entry per driver
    by_driver = {}
    for p in positions:
        dn = p.get("driver_number")
        if dn:
            by_driver[dn] = p

    # Filter top 3
    top3 = sorted(
        [p for p in by_driver.values() if p.get("position") in [1, 2, 3]],
        key=lambda x: x["position"]
    )

    podium = []
    for p in top3:
        drivers = get("drivers", {"session_key": session_key, "driver_number": p["driver_number"]})
        if drivers and isinstance(drivers[0], dict):
            d = drivers[0]
            podium.append({
                "position": p["position"],
                "name": d.get("full_name", "Unknown"),
                "team": d.get("team_name", ""),
            })
    return podium

def update_ics(gp_name, round_num, podium):
    if not podium:
        print("No podium data.")
        return

    winner = podium[0]
    winner_last = winner["name"].split()[-1]
    team = winner["team"]

    medals = ["🥇", "🥈", "🥉"]
    podium_lines = "\\n".join(
        f"{medals[p['position']-1]} {p['name']} ({p['team']})"
        for p in podium
    )

    with open(ICS_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Match race summary line for this round
    pattern = re.compile(
        rf'(SUMMARY:🏁 F1 R{round_num} — .+? · )(.+?)(\n)'
    )
    replacement = rf'\g<1>{winner_last} wins ({team})\3'
    content, n = re.subn(pattern, replacement, content)

    if n == 0:
        print(f"Could not find R{round_num} race event in ICS.")
        return

    with open(ICS_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Updated R{round_num} {gp_name}: {winner['name']} wins ({team})")
    for p in podium:
        print(f"  {p['position']}. {p['name']} ({p['team']})")

def main():
    print("Fetching latest completed race session...")
    session = get_latest_race_session()
    if not session:
        print("No completed races found.")
        return

    gp_name = session.get("meeting_name") or session.get("country_name") or "Unknown"
    session_key = session["session_key"]
    round_num = session.get("meeting_key", "?")

    print(f"Session: {gp_name} (key: {session_key}, meeting: {round_num})")

    podium = get_podium(session_key)
    if not podium:
        print("Could not retrieve podium.")
        return

    update_ics(gp_name, round_num, podium)

if __name__ == "__main__":
    main()
