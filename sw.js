// Offline cache for the scouting apps. Network-first so edits to config.js
// show up when online; falls back to the cached copy when offline.
const CACHE = "5110-frc-scouting-test-v3";
const FILES = ["./", "index.html", "scout.html", "analysis.html", "config.js", "tba.js", "manifest.json",
               "lib/qrcode.js", "lib/jsQR.js"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(FILES)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  // Only cache our own files. TBA downloads are saved to local storage instead.
  if (e.request.method !== "GET" || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
        return res;
      })
      .catch(() => caches.match(e.request, { ignoreSearch: true }))
  );
});
