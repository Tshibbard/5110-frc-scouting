#!/usr/bin/env python3
"""Print "true" if a team in tba-events.txt has an event on today, otherwise "false".

The deploy workflow (.github/workflows/pages.yml) wakes every 30 minutes and runs this to
decide whether to download fresh data. It reads the event dates the site already publishes
(tba/index.json and tba/teams/<team>/<season>.json), so it needs no TBA key.
Usage:  python3 scripts/event_today.py https://your-name.github.io/5110-frc-scouting/

If anything can't be read (first deploy, site down), it prints "true": an extra deploy is
better than a missed one.
"""
import json
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone

# Practice day before, and evening matches that run past midnight UTC after.
MARGIN = timedelta(days=1)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "5110-frc-scouting-test"})
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.load(res)


def event_today(site, today):
    site = site.rstrip("/") + "/"
    index = get(site + "tba/index.json")
    for team, seasons in index.get("teams", {}).items():
        for season in seasons:
            if season not in (today.year, today.year - 1):
                continue
            for e in get(f"{site}tba/teams/{team}/{season}.json"):
                if not e.get("start") or not e.get("end"):
                    continue
                start, end = date.fromisoformat(e["start"]), date.fromisoformat(e["end"])
                if start - MARGIN <= today <= end + MARGIN:
                    return True
    return False


def main():
    site = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if not site:
            raise ValueError("no site URL")
        print("true" if event_today(site, datetime.now(timezone.utc).date()) else "false")
    except Exception as e:
        print(f"::warning::Could not check today's events, deploying anyway: {e!r}", file=sys.stderr)
        print("true")


if __name__ == "__main__":
    main()
