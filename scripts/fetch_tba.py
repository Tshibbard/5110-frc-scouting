#!/usr/bin/env python3
"""Download The Blue Alliance and Statbotics data listed in tba-events.txt into tba/.

The apps read these files from the website, so no device ever needs the TBA key.
GitHub Actions runs this with the TBA_KEY repository secret (.github/workflows/pages.yml).
To try it on your own computer:  TBA_KEY=yourkey python3 scripts/fetch_tba.py

Output:
  tba/index.json                 teams, their seasons, and every event downloaded (for index.html)
  tba/teams/<team>/<season>.json events the team is registered for that season
  tba/<event>/*.json             teams, matches, OPRs, rankings and info for each event (for tba.js)
  tba/<event>/sb_*.json          Statbotics EPAs, match predictions and event summary (optional;
                                 the TBA files are still written when Statbotics is down)
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tba"
API = "https://www.thebluealliance.com/api/v3"
SB_API = "https://api.statbotics.io/v3"  # free, needs no key
KEY = os.environ.get("TBA_KEY") or sys.exit("Set TBA_KEY to your The Blue Alliance read key")
EVENT_RE = re.compile(r"\d{4}[a-z0-9]+")


def get(path, optional=False, api=API):
    """GET an API path. optional: return None instead of stopping when it fails."""
    headers = {"User-Agent": "5110-frc-scouting-test"}
    if api == API:
        headers["X-TBA-Auth-Key"] = KEY
    req = urllib.request.Request(api + path, headers=headers)
    error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return json.load(res)
        except urllib.error.HTTPError as e:
            error = f"HTTP {e.code}"
            if e.code == 401 and api == API:
                sys.exit("TBA rejected the TBA_KEY secret. Check it at thebluealliance.com/account.")
            if e.code == 404:
                break
        except (urllib.error.URLError, TimeoutError) as e:
            error = str(e)
        time.sleep(2 * (attempt + 1))
    if optional:
        return None
    sys.exit(f"Could not download {path}: {error}")


def write(rel, data):
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, separators=(",", ":")))


def event_info(e):
    return {"name": e.get("short_name") or e.get("name") or e["key"], "start": e.get("start_date"),
            "end": e.get("end_date"), "city": e.get("city")}


def sb_get(path):
    """GET a Statbotics path. Always optional: returns None when it fails."""
    return get(path, optional=True, api=SB_API)


def r2(v):
    return round(v, 2) if isinstance(v, (int, float)) and not isinstance(v, bool) else v


def sb_team_years(year, cache={}):  # cache: one download per year per run
    """Every team's season EPA, ranks and record, keyed by team number (one paged download per year)."""
    if year not in cache:
        found, offset = {}, 0
        while True:
            page = sb_get(f"/team_years?year={year}&limit=1000&offset={offset}")
            if not page:
                break
            for t in page:
                found[t.get("team")] = t
            if len(page) < 1000:
                break
            offset += 1000
        cache[year] = found
    return cache[year]


def sb_event(ev):
    """Download Statbotics data for one event and write only what the apps use."""
    team_events = sb_get(f"/team_events?event={ev}&limit=1000")
    if team_events is None:
        print(f"::warning::No Statbotics team data for {ev}")
        return
    seasons = sb_team_years(int(ev[:4]))
    teams, keys = {}, set()
    for te in team_events:
        epa, n = te.get("epa") or {}, te.get("team")
        stats, bd = epa.get("stats") or {}, epa.get("breakdown") or {}
        keys.update(bd)
        ty = seasons.get(n) or {}
        rank = ((ty.get("epa") or {}).get("ranks") or {}).get("total") or {}
        rec = ty.get("record") or {}
        teams[str(n)] = {
            "epa": r2((epa.get("total_points") or {}).get("mean")), "sd": r2((epa.get("total_points") or {}).get("sd")),
            "bd": {k: r2(v) for k, v in bd.items()},
            "start": r2(stats.get("start")), "max": r2(stats.get("max")),
            "rank": rank.get("rank"), "pct": r2(rank.get("percentile")), "count": rank.get("team_count"),
            "rec": f"{rec['wins']}-{rec['losses']}-{rec['ties']}" if rec.get("count") else "",
            "wr": r2(rec.get("winrate")) if rec.get("count") else None,
        }
    # The game-specific names change each season; copy the ones you want into SCOUT_CONFIG.statbotics.
    print(f"Statbotics EPA breakdown names for {ev}: {', '.join(sorted(keys))}")
    write(f"{ev}/sb_team_events.json", teams)

    preds = {}
    for m in sb_get(f"/matches?event={ev}&limit=1000") or []:
        p = m.get("pred") or {}
        if m.get("comp_level") != "qm" or not p:
            continue
        preds[str(m.get("match_number"))] = {
            "rs": r2(p.get("red_score")), "bs": r2(p.get("blue_score")), "rw": r2(p.get("red_win_prob")),
            "rrp": [r2(p.get(f"red_rp_{i}")) for i in (1, 2, 3)], "brp": [r2(p.get(f"blue_rp_{i}")) for i in (1, 2, 3)],
        }
    write(f"{ev}/sb_matches.json", preds)

    e = sb_get(f"/event/{ev}") or {}
    ee, win = e.get("epa") or {}, ((e.get("metrics") or {}).get("win_prob") or {})
    write(f"{ev}/sb_event.json", {"mean": r2(ee.get("mean")), "top8": r2(ee.get("top_8")),
                                  "top24": r2(ee.get("top_24")), "max": r2(ee.get("max")),
                                  "acc": r2(win.get("acc")), "accN": win.get("count")})


def read_list():
    """Parse tba-events.txt into {team: [seasons]} and [event codes]."""
    teams, events = {}, []
    for raw in (ROOT / "tba-events.txt").read_text().splitlines():
        line = raw.split("#")[0].strip().lower()
        if not line:
            continue
        parts = line.split()
        if parts[0] == "team":
            if len(parts) < 3 or not all(p.isdigit() for p in parts[1:]) or not all(len(p) == 4 for p in parts[2:]):
                sys.exit(f"tba-events.txt: use 'team <number> <season> [season …]', not: {raw}")
            teams.setdefault(int(parts[1]), set()).update(int(y) for y in parts[2:])
        elif EVENT_RE.fullmatch(line):
            events.append(line)
        else:
            sys.exit(f"tba-events.txt: not a team line or TBA event code: {raw}")
    return {t: sorted(ys) for t, ys in teams.items()}, events


def main():
    teams, listed = read_list()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    events = {}

    for team, seasons in teams.items():
        for season in seasons:
            found = get(f"/team/frc{team}/events/{season}/simple", optional=True)
            if found is None:
                print(f"::warning::TBA has no team {team} in {season}")
            found = sorted(found or [], key=lambda e: e.get("start_date") or "")
            write(f"teams/{team}/{season}.json", [{"key": e["key"], **event_info(e)} for e in found])
            for e in found:
                events[e["key"]] = event_info(e)
            print(f"Team {team} {season}: {len(found)} events")

    for ev in listed:
        if ev not in events:
            e = get(f"/event/{ev}/simple")  # also checks the code is real
            events[ev] = event_info(e)

    for ev in events:
        write(f"{ev}/teams.json", get(f"/event/{ev}/teams/simple", optional=True) or [])
        write(f"{ev}/matches.json", get(f"/event/{ev}/matches", optional=True) or [])
        # OPRs and rankings don't exist before matches are played.
        write(f"{ev}/oprs.json", get(f"/event/{ev}/oprs", optional=True))
        write(f"{ev}/rankings.json", get(f"/event/{ev}/rankings", optional=True))
        sb_event(ev)
        write(f"{ev}/info.json", {"updated": now})
        print(f"Downloaded {ev}")

    write("index.json", {"updated": now, "teams": {str(t): s for t, s in teams.items()}, "events": events})


if __name__ == "__main__":
    main()
