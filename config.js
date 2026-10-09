// =====================================================================
// Shared scouting configuration — used by BOTH scout.html and analysis.html.
//
// Edit this file to match the current season's game. Each field needs:
//   key    short unique id (kept short so the QR code stays small)
//   label  text shown to the scout
//   type   "counter" | "checkbox" | "select" | "rating" | "text"
//   options  (select only) list of choices
//   max      (rating only) highest rating, default 5
//
// Bump `version` whenever you change fields mid-event so the importer can
// tell old and new QR codes apart.
// =====================================================================
const SCOUT_CONFIG = {
  version: 1,
  appName: "FRC Match Scouting",

  // Official results to pull from TBA's match score breakdown (2026 REBUILT).
  // Update these each season, like the fields below. Only events whose code
  // starts with `year` are read, so testing with an old event gives no junk.
  //   robot    one value per robot. b is the alliance breakdown, i is station 1-3.
  //            The importer shows the average and how often it was above 0.
  //   alliance one value per alliance. With opr: true it is split between the
  //            three teams by least squares (cOPR). With rate: true (0 or 1) it
  //            shows how often the team's alliance achieved it.
  tba: {
    year: 2026,
    robot: [
      { key: "aTwr", label: "Auto tower level", get: (b, i) => towerLevel(b[`autoTowerRobot${i}`]) },
      { key: "eTwr", label: "Endgame tower level", get: (b, i) => towerLevel(b[`endGameTowerRobot${i}`]) },
    ],
    alliance: [
      { key: "fuelA", label: "Auto fuel", get: (b) => b.hubScore?.autoCount, opr: true },
      { key: "fuelT", label: "Teleop fuel", get: (b) => b.hubScore?.teleopCount, opr: true },
      { key: "fuel", label: "Total fuel", get: (b) => b.hubScore?.totalCount, opr: true },
      { key: "twrP", label: "Tower points", get: (b) => b.totalTowerPoints, opr: true },
      { key: "enRP", label: "Energized RP", get: (b) => (b.energizedAchieved ? 1 : 0), rate: true },
      { key: "suRP", label: "Supercharged RP", get: (b) => (b.superchargedAchieved ? 1 : 0), rate: true },
      { key: "trRP", label: "Traversal RP", get: (b) => (b.traversalAchieved ? 1 : 0), rate: true },
    ],
  },

  sections: [
    {
      title: "Autonomous",
      fields: [
        { key: "aMove", label: "Left starting line", type: "checkbox" },
        { key: "aScr", label: "Game pieces scored", type: "counter" },
        { key: "aMis", label: "Game pieces missed", type: "counter" },
        { key: "aClb", label: "Auto climb", type: "checkbox" },
      ],
    },
    {
      title: "Teleop",
      fields: [
        { key: "tScr", label: "Game pieces scored", type: "counter" },
        { key: "tMis", label: "Game pieces missed", type: "counter" },
        { key: "tPas", label: "Pieces passed / fed", type: "counter" },
        { key: "tDef", label: "Played defense", type: "checkbox" },
      ],
    },
    {
      title: "Endgame",
      fields: [
        { key: "eClb", label: "Climb", type: "select",
          options: ["None", "Attempted", "Level 1", "Level 2", "Level 3"] },
      ],
    },
    {
      title: "Overall",
      fields: [
        { key: "oDrv", label: "Driver skill", type: "rating", max: 5 },
        { key: "oDef", label: "Defense rating", type: "rating", max: 5 },
        { key: "oBrk", label: "Robot broke / disabled", type: "checkbox" },
        { key: "oCrd", label: "Yellow / red card", type: "checkbox" },
        { key: "oNot", label: "Notes", type: "text" },
      ],
    },
  ],
};

// TBA reports tower climbs as "None", "Level1", "Level2" or "Level3"; turn that into 0-3.
function towerLevel(s) { return Number(String(s ?? "").match(/\d/)?.[0] ?? 0); }

// Identifies our QR codes so the importer ignores anything else it scans.
const QR_PREFIX = "FRCS:";

// Every field in display order (handy for tables and CSV columns).
SCOUT_CONFIG.allFields = SCOUT_CONFIG.sections.flatMap((s) =>
  s.fields.map((f) => ({ ...f, section: s.title }))
);
