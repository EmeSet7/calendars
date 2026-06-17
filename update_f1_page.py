import requests
import json
from datetime import datetime, timezone

OUTPUT = "f1.html"
JOLPICA = "https://api.jolpi.ca/ergast/f1"
OPENF1 = "https://api.openf1.org/v1"

TEAM_COLORS = {
    "mercedes": "#00D2BE",
    "ferrari": "#E8002D",
    "red bull": "#3671C6",
    "mclaren": "#FF8000",
    "aston martin": "#229971",
    "alpine": "#0093CC",
    "williams": "#64C4FF",
    "haas": "#B6BABD",
    "sauber": "#52E252",
    "racing bulls": "#6692FF",
}

def team_color(team_name):
    t = team_name.lower()
    for key, color in TEAM_COLORS.items():
        if key in t:
            return color
    return "#888888"

def get_driver_standings():
    r = requests.get(f"{JOLPICA}/2026/driverStandings.json", timeout=10)
    data = r.json()
    standings = data["MRData"]["StandingsTable"]["StandingsLists"]
    if not standings:
        return []
    return standings[0]["DriverStandings"]

def get_constructor_standings():
    r = requests.get(f"{JOLPICA}/2026/constructorStandings.json", timeout=10)
    data = r.json()
    standings = data["MRData"]["StandingsTable"]["StandingsLists"]
    if not standings:
        return []
    return standings[0]["ConstructorStandings"]

def get_race_results():
    r = requests.get(f"{JOLPICA}/2026/results.json?limit=200", timeout=10)
    data = r.json()
    races = data["MRData"]["RaceTable"]["Races"]
    return races

def get_fastest_laps(races):
    """Extract fastest lap per race from results."""
    fastest = []
    for race in races:
        fl = None
        fl_time = None
        for result in race.get("Results", []):
            lap_data = result.get("FastestLap", {})
            if lap_data.get("rank") == "1":
                fl = result
                fl_time = lap_data.get("Time", {}).get("time", "N/A")
                break
        if fl:
            fastest.append({
                "round": race["round"],
                "race": race["raceName"].replace(" Grand Prix", " GP"),
                "driver": f"{fl['Driver']['givenName']} {fl['Driver']['familyName']}",
                "team": fl["Constructor"]["name"],
                "time": fl_time,
            })
    return fastest

def generate_html(driver_standings, constructor_standings, fastest_laps, races):
    updated = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    last_race = races[-1]["raceName"].replace(" Grand Prix", " GP") if races else "—"
    last_round = races[-1]["round"] if races else "—"

    # Driver standings rows
    driver_rows = ""
    for i, d in enumerate(driver_standings[:10]):
        driver = d["Driver"]
        constructor = d["Constructors"][0]
        color = team_color(constructor["name"])
        name = f"{driver['givenName']} {driver['familyName']}"
        pos = d["position"]
        pts = d["points"]
        wins = d["wins"]
        pos_icon = "🥇" if pos == "1" else "🥈" if pos == "2" else "🥉" if pos == "3" else pos
        driver_rows += f"""
        <tr>
            <td class="pos">{pos_icon}</td>
            <td class="name">{name}<span class="team-dot" style="background:{color}"></span></td>
            <td class="team">{constructor['name']}</td>
            <td class="pts">{pts}</td>
            <td class="wins">{wins}</td>
        </tr>"""

    # Constructor standings rows
    constructor_rows = ""
    for c in constructor_standings[:10]:
        constructor = c["Constructor"]
        color = team_color(constructor["name"])
        pos = c["position"]
        pos_icon = "🥇" if pos == "1" else "🥈" if pos == "2" else "🥉" if pos == "3" else pos
        constructor_rows += f"""
        <tr>
            <td class="pos">{pos_icon}</td>
            <td class="name"><span class="team-bar" style="background:{color}"></span>{constructor['name']}</td>
            <td class="pts">{c['points']}</td>
            <td class="wins">{c['wins']}</td>
        </tr>"""

    # Fastest laps rows
    fl_rows = ""
    for fl in fastest_laps:
        color = team_color(fl["team"])
        fl_rows += f"""
        <tr>
            <td class="round">R{fl['round']}</td>
            <td class="race">{fl['race']}</td>
            <td class="name">{fl['driver']}<span class="team-dot" style="background:{color}"></span></td>
            <td class="time">{fl['time']}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>F1 2026 — Season Tracker</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: #0d0d0d;
    color: #e0e0e0;
    font-family: 'Segoe UI', system-ui, sans-serif;
    padding: 24px 16px;
    min-height: 100vh;
  }}

  header {{
    text-align: center;
    margin-bottom: 32px;
  }}

  header h1 {{
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
  }}

  header h1 span {{ color: #e10600; }}

  .meta {{
    font-size: 0.75rem;
    color: #666;
    margin-top: 6px;
  }}

  .grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    max-width: 1100px;
    margin: 0 auto;
  }}

  .card {{
    background: #111111;
    border-radius: 10px;
    padding: 20px;
    border: 1px solid #1e1e1e;
  }}

  .card.full {{ grid-column: 1 / -1; }}

  .card h2 {{
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #666;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid #1e1e1e;
  }}

  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
  }}

  th {{
    text-align: left;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #444;
    padding: 0 8px 10px 8px;
  }}

  td {{
    padding: 9px 8px;
    border-top: 1px solid #1a1a1a;
  }}

  tr:first-child td {{ border-top: none; }}

  td.pos {{ width: 36px; font-weight: 700; color: #fff; }}
  td.pts {{ font-weight: 700; color: #fff; text-align: right; }}
  td.wins {{ color: #666; text-align: right; }}
  td.time {{ font-family: monospace; color: #e10600; font-size: 0.85rem; }}
  td.round {{ color: #444; font-size: 0.75rem; width: 36px; }}
  td.race {{ color: #aaa; }}
  td.team {{ color: #666; font-size: 0.8rem; }}

  .team-dot {{
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-left: 7px;
    vertical-align: middle;
    flex-shrink: 0;
  }}

  .team-bar {{
    display: inline-block;
    width: 3px;
    height: 14px;
    border-radius: 2px;
    margin-right: 8px;
    vertical-align: middle;
  }}

  tr:hover td {{ background: #161616; }}

  @media (max-width: 640px) {{
    .grid {{ grid-template-columns: 1fr; }}
    .card.full {{ grid-column: 1; }}
    td.team {{ display: none; }}
  }}
</style>
</head>
<body>

<header>
  <h1>F1 <span>2026</span></h1>
  <p class="meta">After R{last_round} · {last_race} · Updated {updated}</p>
</header>

<div class="grid">

  <div class="card">
    <h2>Driver Standings</h2>
    <table>
      <thead>
        <tr>
          <th></th>
          <th>Driver</th>
          <th>Team</th>
          <th style="text-align:right">Pts</th>
          <th style="text-align:right">W</th>
        </tr>
      </thead>
      <tbody>{driver_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>Constructor Standings</h2>
    <table>
      <thead>
        <tr>
          <th></th>
          <th>Team</th>
          <th style="text-align:right">Pts</th>
          <th style="text-align:right">W</th>
        </tr>
      </thead>
      <tbody>{constructor_rows}</tbody>
    </table>
  </div>

  <div class="card full">
    <h2>Fastest Laps</h2>
    <table>
      <thead>
        <tr>
          <th></th>
          <th>Race</th>
          <th>Driver</th>
          <th>Time</th>
        </tr>
      </thead>
      <tbody>{fl_rows}</tbody>
    </table>
  </div>

</div>

</body>
</html>"""

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Generated {OUTPUT}")

def main():
    print("Fetching driver standings...")
    driver_standings = get_driver_standings()

    print("Fetching constructor standings...")
    constructor_standings = get_constructor_standings()

    print("Fetching race results...")
    races = get_race_results()

    print("Extracting fastest laps...")
    fastest_laps = get_fastest_laps(races)

    print(f"Generating HTML — {len(races)} races, {len(fastest_laps)} fastest laps...")
    generate_html(driver_standings, constructor_standings, fastest_laps, races)

if __name__ == "__main__":
    main()
