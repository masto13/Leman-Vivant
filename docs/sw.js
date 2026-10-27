// Mode hors ligne du site Le monde des vivants (accueil et atlas).
// Les pages sont chargées depuis le réseau en priorité (pour avoir les données du jour),
// et depuis le cache quand il n'y a pas de connexion.
const CACHE = "mdv-v3";
const CORE = ["/", "/leman/"];

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
  // Demandes que le navigateur doit traiter seul (sinon fetch() échoue et l'icône de l'iPhone ne se charge pas)
  if (req.cache === "only-if-cached" && req.mode !== "same-origin") return;
  const url = new URL(req.url);
  // Icônes et manifestes : jamais interceptés, l'iPhone les lit directement pour l'écran d'accueil
  if (url.origin === location.origin && /^\/(icons\/|apple-touch-icon|favicon|[\w-]*\.?manifest|accueil\.webmanifest)/.test(url.pathname)) return;
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
