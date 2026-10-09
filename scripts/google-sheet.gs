// Google Sheet backup for the scouting apps (see "Google Sheet backup" in README.md).
//
// Paste this whole file into the Sheet's Extensions → Apps Script editor, then
// Deploy → New deployment → Web app, "Execute as: Me", "Who has access: Anyone".
// The web-app URL it gives you is what the apps need. Keep it private: anyone
// who has it can add rows.
//
// POST {records: [...], labels: {key: "Column label"}}  adds or replaces matches
// GET  ?event=2026miket (optional)                      returns {records: [...]}
//
// One row per event + match + driver station. A newer save replaces the row.
// Row 1 shows labels; each header cell's note holds its field key, so labels
// can be renamed without breaking anything. The last column ("json") keeps the
// exact record, which is what the apps read back.

const SHEET_NAME = "Matches";
const JSON_COL = "json";
const FIRST_KEYS = ["_e", "_m", "_t", "_p", "_s", "_n", "_v", "_ts"];

function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    const body = JSON.parse(e.postData.contents);
    const saved = save_(body.records || [], body.labels || {});
    return json_({ ok: true, saved: saved });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  } finally {
    lock.releaseLock();
  }
}

function doGet(e) {
  const event = String((e.parameter && e.parameter.event) || "").trim().toLowerCase();
  const sheet = sheet_();
  const keys = keys_(sheet);
  const col = keys.indexOf(JSON_COL);
  const records = [];
  if (sheet.getLastRow() > 1) {
    const vals = sheet.getRange(2, col + 1, sheet.getLastRow() - 1, 1).getValues();
    for (const [text] of vals) {
      if (!text) continue;
      try {
        const rec = JSON.parse(text);
        if (!event || rec._e === event) records.push(rec);
      } catch (err) {}
    }
  }
  return json_({ ok: true, records: records });
}

function save_(records, labels) {
  const sheet = sheet_();
  let keys = keys_(sheet);

  // Add a column for any field this sheet hasn't seen, just before "json".
  for (const rec of records) {
    for (const k of Object.keys(rec)) {
      if (keys.indexOf(k) >= 0) continue;
      const at = keys.indexOf(JSON_COL) + 1;
      sheet.insertColumnBefore(at);
      sheet.getRange(1, at).setValue(labels[k] || k).setNote(k);
      keys = keys_(sheet);
    }
  }

  const id = (r) => [r._e, r._m, r._p].join("|");
  const rows = {};
  const last = sheet.getLastRow();
  const jsonCol = keys.indexOf(JSON_COL) + 1;
  if (last > 1) {
    sheet.getRange(2, jsonCol, last - 1, 1).getValues().forEach(([text], i) => {
      try { const r = JSON.parse(text); rows[id(r)] = { row: i + 2, ts: r._ts || 0 }; } catch (err) {}
    });
  }

  const saved = [];
  for (const rec of records) {
    if (!rec || !rec._e || !rec._m || !rec._p) continue;
    const have = rows[id(rec)];
    // An older save never replaces a newer one.
    if (!have || (rec._ts || 0) >= have.ts) {
      const row = have ? have.row : sheet.getLastRow() + 1;
      const values = keys.map((k) => (k === JSON_COL ? JSON.stringify(rec) : rec[k] === undefined ? "" : rec[k]));
      // Text stays text, so notes like "3-4" don't turn into dates.
      const formats = values.map((v) => (typeof v === "string" ? "@" : "General"));
      sheet.getRange(row, 1, 1, keys.length).setNumberFormats([formats]).setValues([values]);
      rows[id(rec)] = { row: row, ts: rec._ts || 0 };
    }
    saved.push(id(rec) + "|" + rec._ts);
  }
  return saved;
}

function sheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    const labels = ["Event", "Match", "Team", "Station", "Scout", "No-show", "Cfg ver", "Saved at", "json"];
    const keys = FIRST_KEYS.concat([JSON_COL]);
    const head = sheet.getRange(1, 1, 1, keys.length);
    head.setValues([labels]).setNotes([keys]).setFontWeight("bold");
    sheet.setFrozenRows(1);
  }
  return sheet;
}

// Field key of each column, from the header notes.
function keys_(sheet) {
  return sheet.getRange(1, 1, 1, sheet.getLastColumn()).getNotes()[0];
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
