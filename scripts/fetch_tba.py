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
            if not isinstance(page, list) or not page:
                break
            for t in page:
                found[obj(t).get("team")] = t
            if len(page) < 1000:
                break
            offset += 1000
        cache[year] = found
    return cache[year]


def num(v, key="mean"):
    """A number from Statbotics, which may send it bare or as {mean, sd}. None if it is neither."""
    if isinstance(v, dict):
        v = v.get(key)
    return r2(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def obj(v):
    return v if isinstance(v, dict) else {}


def show_shape(name, sample):
    """Print the keys Statbotics sent, so field names can be checked in the Actions log."""
    if isinstance(sample, dict):
        print(f"{name}: " + ", ".join(f"{k}{'{…}' if isinstance(v, dict) else ''}" for k, v in sample.items()))
        for k, v in sample.items():
            if isinstance(v, dict) and k in ("epa", "pred", "metrics", "record"):
                show_shape(f"{name}.{k}", v)


shape_shown = False


def sb_event(ev):
    """Download Statbotics data for one event and write only what the apps use."""
    global shape_shown
    team_events = sb_get(f"/team_events?event={ev}&limit=1000")
    if not isinstance(team_events, list):
        print(f"::warning::No Statbotics team data for {ev}")
        return
    matches = sb_get(f"/matches?event={ev}&limit=1000")
    e = obj(sb_get(f"/event/{ev}"))
    if not shape_shown:
        shape_shown = True
        print("::group::Statbotics response shape")
        show_shape("team_event", team_events[0] if team_events else None)
        show_shape("match", matches[0] if isinstance(matches, list) and matches else None)
        show_shape("event", e)
        print("::endgroup::")

    seasons = sb_team_years(int(ev[:4]))
    teams, keys = {}, set()
    for te in team_events:
        te = obj(te)
        epa, n = obj(te.get("epa")), te.get("team")
        stats = obj(epa.get("stats"))
        bd = {k: num(v) for k, v in obj(epa.get("breakdown")).items() if num(v) is not None}
        keys.update(bd)
        ty = obj(seasons.get(n))
        rank = obj(obj(obj(ty.get("epa")).get("ranks")).get("total"))
        rec = obj(ty.get("record"))
        total = epa.get("total_points")
        teams[str(n)] = {
            "epa": num(total), "sd": num(total, "sd") if isinstance(total, dict) else num(epa.get("total_points_sd")),
            "bd": bd, "start": num(stats.get("start")), "max": num(stats.get("max")),
            "rank": num(rank.get("rank")), "pct": num(rank.get("percentile")), "count": num(rank.get("team_count")),
            "rec": f"{rec.get('wins', 0)}-{rec.get('losses', 0)}-{rec.get('ties', 0)}" if rec.get("count") else "",
            "wr": num(rec.get("winrate")) if rec.get("count") else None,
        }
    # The game-specific names change each season; copy the ones you want into SCOUT_CONFIG.statbotics.
    print(f"Statbotics EPA breakdown names for {ev}: {', '.join(sorted(keys))}")
    write(f"{ev}/sb_team_events.json", teams)

    preds = {}
    for m in matches if isinstance(matches, list) else []:
        m = obj(m)
        p = obj(m.get("pred"))
        if m.get("comp_level") != "qm" or not p:
            continue
        preds[str(m.get("match_number"))] = {
            "rs": num(p.get("red_score")), "bs": num(p.get("blue_score")), "rw": num(p.get("red_win_prob")),
            "rrp": [num(p.get(f"red_rp_{i}")) for i in (1, 2, 3)], "brp": [num(p.get(f"blue_rp_{i}")) for i in (1, 2, 3)],
        }
    write(f"{ev}/sb_matches.json", preds)

    ee, win = obj(e.get("epa")), obj(obj(e.get("metrics")).get("win_prob"))
    write(f"{ev}/sb_event.json", {"mean": num(ee.get("mean")), "top8": num(ee.get("top_8")),
                                  "top24": num(ee.get("top_24")), "max": num(ee.get("max")),
                                  "acc": num(win.get("acc")), "accN": num(win.get("count"))})


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
        try:
            sb_event(ev)
        except Exception as e:  # Statbotics is extra; never let it stop the TBA data from publishing
            print(f"::warning::Statbotics data for {ev} skipped: {e!r}")
        write(f"{ev}/info.json", {"updated": now})
        print(f"Downloaded {ev}")

    write("index.json", {"updated": now, "teams": {str(t): s for t, s in teams.items()}, "events": events})


if __name__ == "__main__":
    main()
