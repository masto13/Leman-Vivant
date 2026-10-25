// Mode hors ligne du site Le monde des vivants (accueil et atlas).
// Les pages sont chargées depuis le réseau en priorité (pour avoir les données du jour),
// et depuis le cache quand il n'y a pas de connexion.
const CACHE = "mdv-v2";
const CORE = ["/", "/leman/", "/manifest.webmanifest", "/icons/icon-192.png", "/icons/icon-512.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  const isPage = req.mode === "navigate" || url.pathname.endsWith(".html");
  const isLib = /cdnjs\.cloudflare\.com|fonts\.(googleapis|gstatic)\.com/.test(url.host);
  if (isPage) {
    // réseau d'abord : les données changent chaque jour
    e.respondWith(fetch(req).then(res => {
      const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); return res;
    }).catch(() => caches.match(req, {ignoreSearch: true})
      .then(r => r || caches.match(url.pathname.startsWith("/leman") ? "/leman/" : "/"))));
  } else if (url.origin === location.origin || isLib) {
    // cache d'abord : icônes, photos, bibliothèque de graphiques, polices
    e.respondWith(caches.match(req).then(r => r || fetch(req).then(res => {
      if (res.ok || res.type === "opaque") { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
      return res;
    })));
  }
});
