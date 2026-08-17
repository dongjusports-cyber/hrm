/* PWA Worker — icon/manifest cache; HTML/JS/CSS luôn network-first (tránh màn hình trắng sau deploy). */
const CACHE = "dj-hrm-worker-v7";
const STATIC_ASSETS = [
  "/manifest.json",
  "/manifest.webmanifest",
  "/dj-logo.png",
  "/icon-192.png",
  "/icon-512.png",
];

function isAppShell(url) {
  if (url.pathname.startsWith("/assets/")) return true;
  if (url.pathname.endsWith(".js") || url.pathname.endsWith(".css")) return true;
  return false;
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(STATIC_ASSETS)).then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // SPA + bundle: luôn lấy mạng trước — cache cũ gây 404 JS → màn hình trắng
  if (req.mode === "navigate" || isAppShell(url)) {
    event.respondWith(
      fetch(req).catch(async () => {
        const cached = await caches.match(req);
        if (cached) return cached;
        if (req.mode === "navigate") {
          return caches.match("/worker/login");
        }
        throw new Error("offline");
      }),
    );
    return;
  }

  // Icon/manifest: stale-while-revalidate
  event.respondWith(
    caches.match(req).then((cached) => {
      const network = fetch(req)
        .then((res) => {
          if (res.ok) {
            const clone = res.clone();
            void caches.open(CACHE).then((c) => c.put(req, clone));
          }
          return res;
        })
        .catch(() => cached);
      return cached || network;
    }),
  );
});
