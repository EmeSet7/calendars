#!/usr/bin/env python3
"""
build_motorsports_ics.py
────────────────────────
Reads motorsports_events.yml and writes motorsports_2026.ics.

Usage:
    python build_motorsports_ics.py
    python build_motorsports_ics.py --yaml my_events.yml --out calendar.ics

Edit events in the YAML file, then re-run. ICS is rebuilt from scratch each time.
"""

import argparse
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

try:
    import yaml
except ImportError:
    sys.exit("PyYAML not found. Run: pip install pyyaml")

# ── Series display config ───────────────────────────────────────────────────
SERIES_META = {
    "NASCAR":    {"label": "NASCAR Cup Series",                "emoji": "🏁"},
    "NASCAR_B":  {"label": "NASCAR O'Reilly Auto Parts Series","emoji": "🏁"},
    "NASCAR_T":  {"label": "NASCAR Craftsman Trucks",          "emoji": "🏁"},
    "WEC":       {"label": "FIA WEC",                          "emoji": "⏱️"},
    "IMSA":      {"label": "IMSA WeatherTech",                 "emoji": "🇺🇸"},
    "IGTC":      {"label": "Intercontinental GT Challenge",    "emoji": "🌍"},
    "GTWCE":     {"label": "GT World Challenge Europe",        "emoji": "🏆"},
    "24H":       {"label": "24h Race",                         "emoji": "🌙"},
    "SUPERCARS": {"label": "Supercars Championship (V8)",      "emoji": "🦘"},
    "DTM":       {"label": "DTM",                              "emoji": "🇩🇪"},
    "TCR":       {"label": "TCR World Tour",                   "emoji": "🔄"},
    "RALLY":     {"label": "Rally-Raid / Dakar",               "emoji": "🏜️"},
}

# ── ICS helpers ─────────────────────────────────────────────────────────────
def ics_dt(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ")

def fold(line: str) -> str:
    """RFC 5545 line folding (75-octet max)."""
    encoded = line.encode("utf-8")
    if len(encoded) <= 75:
        return line
    chunks, pos = [], 0
    while pos < len(encoded):
        cut = 75 if pos == 0 else 74
        chunk = encoded[pos : pos + cut]
        while True:
            try:
                chunk.decode("utf-8"); break
            except UnicodeDecodeError:
                chunk = chunk[:-1]
        chunks.append(("" if pos == 0 else " ") + chunk.decode("utf-8"))
        pos += len(chunk)
    return "\r\n".join(chunks)

def parse_dt(raw) -> datetime:
    if isinstance(raw, datetime):
        return raw.replace(tzinfo=timezone.utc) if raw.tzinfo is None else raw
    raw = str(raw).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    raise ValueError(f"Cannot parse date: {raw!r}")

# ── Main builder ─────────────────────────────────────────────────────────────
def build_ics(events: list, out_path: Path) -> int:
    now_str = ics_dt(datetime.now(timezone.utc))
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Motorsports Calendar 2026//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Motorsports 2026",
        "X-WR-CALDESC:WEC · IMSA · IGTC · GTWCE · NASCAR · Supercars · DTM · Dakar — no single-seaters",
        "X-WR-TIMEZONE:UTC",
        "X-APPLE-CALENDAR-COLOR:#E8C547",
    ]

    for ev in events:
        series  = str(ev.get("series", "")).upper()
        meta    = SERIES_META.get(series, {"label": series, "emoji": "🏎️"})
        name    = str(ev.get("name", "Unnamed Event"))
        venue   = str(ev.get("venue", ""))
        location = str(ev.get("location", ""))
        done    = bool(ev.get("done", False))

        dtstart = parse_dt(ev["start"])
        dtend   = parse_dt(ev["end"])

        title = f"{meta['emoji']} {name}"
        desc_parts = [f"Series: {meta['label']}"]
        if venue:    desc_parts.append(f"Venue: {venue}")
        if location: desc_parts.append(f"Location: {location}")
        if done:     desc_parts.append("Status: COMPLETED ✓")
        description = "\\n".join(desc_parts)

        loc_str = ", ".join(filter(None, [venue, location]))
        uid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"motorsports2026-{series}-{name}-{ev['start']}"))

        lines += [
            "BEGIN:VEVENT",
            fold(f"UID:{uid}"),
            f"DTSTAMP:{now_str}",
            f"DTSTART:{ics_dt(dtstart)}",
            f"DTEND:{ics_dt(dtend)}",
            fold(f"SUMMARY:{title}"),
            fold(f"DESCRIPTION:{description}"),
            fold(f"LOCATION:{loc_str}"),
            f"STATUS:{'CONFIRMED' if not done else 'COMPLETED'}",
            fold(f"CATEGORIES:{meta['label']}"),
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    out_path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return len(events)

# ── CLI ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Build motorsports ICS from YAML")
    parser.add_argument("--yaml", default="motorsports_events.yml")
    parser.add_argument("--out",  default="motorsports_2026.ics")
    args = parser.parse_args()

    yaml_path = Path(args.yaml)
    if not yaml_path.exists():
        sys.exit(f"YAML not found: {yaml_path}")

    with yaml_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    events = data.get("events", [])
    if not events:
        sys.exit("No events found in YAML.")

    events.sort(key=lambda e: str(e.get("start", "")))

    out_path = Path(args.out)
    count = build_ics(events, out_path)
    print(f"✓ {count} events → {out_path}\n")

    series_count = Counter(str(e.get("series","?")).upper() for e in events)
    for s, n in sorted(series_count.items()):
        meta = SERIES_META.get(s, {"emoji": "🏎️", "label": s})
        print(f"  {meta['emoji']}  {meta['label']}: {n}")

if __name__ == "__main__":
    main()
