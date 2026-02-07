/* Minimal offline cache for the commercial pack (static-only). */
const CACHE = 'aimath-commercial-pack1-fraction-sprint-v1';

const ASSETS = [
  './',
  './index.html',
  './bank.js',
  './manifest.json',
  './icon.svg'
];

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await cache.addAll(ASSETS);
    self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.map((k) => (k === CACHE ? Promise.resolve() : caches.delete(k))));
    self.clients.claim();
  })());
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  event.respondWith((async () => {
    const url = new URL(req.url);

    // Only handle same-origin requests within this folder scope.
    if (url.origin !== self.location.origin) return fetch(req);

    const cached = await caches.match(req, { ignoreSearch: true });
    if (cached) return cached;

    try {
      const res = await fetch(req);
      const cache = await caches.open(CACHE);
      cache.put(req, res.clone());
      return res;
    } catch {
      // Offline fallback: root.
      const fallback = await caches.match('./index.html');
      return fallback || new Response('Offline', { status: 503, headers: { 'Content-Type': 'text/plain' } });
    }
  })());
});
