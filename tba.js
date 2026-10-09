// =====================================================================
// The Blue Alliance data — used by BOTH scout.html and analysis.html.
//
// The TBA key never reaches the browser. A GitHub Actions workflow downloads
// the events listed in tba-events.txt into tba/<event>/*.json and publishes
// them with the site (see scripts/fetch_tba.py). This file reads those files.
//
// Internet is only needed while downloading. The result is kept in local
// storage, so the apps keep working offline at the event. Press the button
// again when you are online to pick up new scores, OPRs and rankings.
//
// Only qualification matches are used, because the scout app numbers
// matches 1, 2, 3… and playoff matches don't fit that scheme.
// Which score-breakdown values are kept is set by SCOUT_CONFIG.tba in config.js.
// =====================================================================
const TBA = (() => {
  const LS_DATA = "frcs.tba.data";
  const STATIONS = ["R1", "R2", "R3", "B1", "B2", "B3"];
  const teamNum = (key) => parseInt(String(key).replace(/^frc/, ""), 10);

  function load(k, fallback) {
    try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : fallback; }
    catch { return fallback; }
  }
  function store(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} }

  let data = load(LS_DATA, null);

  const eventKey = (ev) => String(ev || "").trim().toLowerCase();

  async function get(ev, name) {
    let res;
    // no-store: always ask the site for the newest copy, not the browser cache.
    try { res = await fetch(`tba/${ev}/${name}.json`, { cache: "no-store" }); }
    catch { throw new Error("Could not reach the scouting website. Check the internet connection."); }
    if (res.status === 404) {
      throw new Error(`The website has no TBA data for ${ev}. Add it to tba-events.txt on GitHub and wait for the site to update.`);
    }
    if (!res.ok) throw new Error(`Website error ${res.status}. Try again in a minute.`);
    return res.json();
  }

  async function download(ev) {
    ev = eventKey(ev);
    if (!ev) throw new Error("Enter the event code first.");
    if (location.protocol === "file:") {
      throw new Error("TBA data only works on the website (or localhost), not on a file opened from disk.");
    }

    // OPRs and rankings don't exist until matches are played, so they may be null.
    const [teams, matches, oprs, rankings, info] = await Promise.all([
      get(ev, "teams"), get(ev, "matches"),
      get(ev, "oprs").catch(() => null), get(ev, "rankings").catch(() => null),
      get(ev, "info").catch(() => null),
    ]);

    // fetched = when GitHub last downloaded it from TBA.
    const d = { event: ev, fetched: Date.parse(info?.updated) || Date.now(), teams: {}, matches: {}, oprs: {}, ranks: {},
                rsName: rankings?.sort_order_info?.[0]?.name || "Ranking score" };
    for (const t of teams || []) d.teams[t.team_number] = t.nickname || "";

    const game = SCOUT_CONFIG.tba;
    const readBreakdown = game && ev.startsWith(String(game.year));

    for (const m of matches || []) {
      if (m.comp_level !== "qm") continue;
      // team_keys are in driver station order: index 0 = station 1.
      const row = {};
      ["red", "blue"].forEach((c) =>
        m.alliances[c].team_keys.forEach((k, i) => { row[c[0].toUpperCase() + (i + 1)] = teamNum(k); }));
      // TBA uses -1 for matches that haven't been played.
      row.rs = m.alliances.red.score >= 0 ? m.alliances.red.score : null;
      row.bs = m.alliances.blue.score >= 0 ? m.alliances.blue.score : null;
      if (readBreakdown && m.score_breakdown) row.g = breakdown(m.score_breakdown, game);
      d.matches[m.match_number] = row;
    }

    for (const [k, opr] of Object.entries(oprs?.oprs || {})) {
      d.oprs[teamNum(k)] = { opr, dpr: oprs.dprs?.[k], ccwm: oprs.ccwms?.[k] };
    }
    for (const r of rankings?.rankings || []) {
      const rec = r.record;
      d.ranks[teamNum(r.team_key)] = {
        rank: r.rank,
        rec: rec ? `${rec.wins}-${rec.losses}-${rec.ties}` : "",
        rs: r.sort_orders?.[0] ?? null,
      };
    }

    data = d;
    store(LS_DATA, d);
    return d;
  }

  // Game-specific values: g.R1…g.B3 per robot, g.red / g.blue per alliance.
  function breakdown(sb, game) {
    const g = {};
    for (const c of ["red", "blue"]) {
      const b = sb[c];
      if (!b) continue;
      const pick = (fields, ...args) => Object.fromEntries(fields.map((f) => {
        let v;
        try { v = f.get(b, ...args); } catch { v = null; }
        return [f.key, v ?? null];
      }));
      g[c] = pick(game.alliance || []);
      for (let i = 1; i <= 3; i++) g[c[0].toUpperCase() + i] = pick(game.robot || [], i);
    }
    return g;
  }

  // Downloaded data, but only when it is for this event.
  const forEvent = (ev) => (data && data.event === eventKey(ev) ? data : null);

  return {
    STATIONS, download, forEvent,
    get data() { return data; },
    // The team TBA has in this match and driver station, or null.
    scheduled: (ev, match, station) => forEvent(ev)?.matches[match]?.[station] ?? null,
    teamName: (team) => data?.teams[team] || "",
  };
})();
