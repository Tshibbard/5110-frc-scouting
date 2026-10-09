// =====================================================================
// Google Sheet backup — used by BOTH scout.html and analysis.html.
//
// The Sheet runs scripts/google-sheet.gs as a web app. Its URL is entered on
// each device (or arrives in a setup link, #sheet=…) and kept in local storage,
// never in this repository, so people who only open the website don't get it.
//
// Scout sends every saved match and remembers which ones the Sheet has
// confirmed, so matches saved offline go out once the internet is back.
// Analysis pulls everyone's matches from the Sheet.
// =====================================================================
const SHEET = (() => {
  const LS_URL = "frcs.sheet.url", LS_SENT = "frcs.sheet.sent";
  const URL_RE = /^https:\/\/script\.google\.com\/macros\/s\/[\w-]+\/exec$/;

  function load(k, fallback) {
    try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : fallback; }
    catch { return fallback; }
  }
  function store(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} }

  // One id per saved version of a match, so a re-save is sent again.
  const version = (r) => `${r._e}|${r._m}|${r._p}|${r._ts}`;

  const url = () => load(LS_URL, "");
  function setUrl(u) {
    u = String(u || "").trim();
    if (u && !URL_RE.test(u)) {
      throw new Error("That isn't an Apps Script web-app URL. It starts with https://script.google.com/macros/s/ and ends with /exec.");
    }
    store(LS_URL, u);
  }

  // A setup link (…#sheet=<url>) stores the URL, then the hash is removed from
  // the address bar so it isn't bookmarked or shared by accident.
  function fromLink() {
    const m = location.hash.match(/(?:^#|&)sheet=([^&]+)/);
    if (!m) return false;
    try { setUrl(decodeURIComponent(m[1])); } catch { return false; }
    history.replaceState(null, "", location.pathname + location.search);
    return true;
  }
  const setupLink = (page) => `${new URL(page, location.href).href.split("#")[0]}#sheet=${encodeURIComponent(url())}`;

  async function call(options, query = "") {
    if (!url()) throw new Error("No Google Sheet URL is set on this device.");
    let res;
    try { res = await fetch(url() + query, options); }
    catch { throw new Error("Could not reach the Google Sheet. Check the internet connection."); }
    if (!res.ok) throw new Error(`Google Sheet error ${res.status}.`);
    let body;
    try { body = await res.json(); }
    catch { throw new Error("The Google Sheet didn't answer. Check the URL and that the web app allows Anyone."); }
    if (!body.ok) throw new Error(`Google Sheet: ${body.error || "unknown error"}`);
    return body;
  }

  const isSent = (r) => load(LS_SENT, []).includes(version(r));

  // Send every saved match the Sheet hasn't confirmed. Returns how many were sent.
  let sending = null;
  function sendPending(hist) {
    if (sending) return sending;
    sending = (async () => {
      const sent = new Set(load(LS_SENT, []));
      const todo = hist.filter((r) => !sent.has(version(r)));
      if (!todo.length) return 0;
      const labels = {};
      for (const f of SCOUT_CONFIG.allFields) labels[f.key] = f.label;
      // text/plain keeps this a "simple" request, which Apps Script accepts from any site.
      const body = await call({ method: "POST", headers: { "Content-Type": "text/plain" },
                                body: JSON.stringify({ records: todo, labels }) });
      for (const v of body.saved || []) sent.add(v);
      store(LS_SENT, [...sent]);
      return todo.length;
    })().finally(() => { sending = null; });
    return sending;
  }

  async function pull(event) {
    const q = event ? `?event=${encodeURIComponent(String(event).trim().toLowerCase())}` : "";
    const records = (await call({ cache: "no-store" }, q)).records || [];
    // The Sheet has these already, so they are never sent back.
    const sent = new Set(load(LS_SENT, []));
    for (const r of records) sent.add(version(r));
    store(LS_SENT, [...sent]);
    return records;
  }

  return { url, setUrl, fromLink, setupLink, isSent, sendPending, pull };
})();
