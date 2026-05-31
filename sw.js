// v10 - Never cache HTML, network-first for all
const CACHE = 'commit-v10';

self.addEventListener('install', e => { self.skipWaiting(); });
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k)))));
  e.waitUntil(clients.claim());
});

self.addEventListener('fetch', e => {
  // Never serve HTML from cache - always go to network
  if (e.request.destination === 'document') {
    e.respondWith(fetch(e.request));
    return;
  }
  // Other assets: network first, cache fallback
  e.respondWith(
    fetch(e.request).then(resp => {
      const clone = resp.clone();
      caches.open(CACHE).then(c => c.put(e.request, clone));
      return resp;
    }).catch(() => caches.match(e.request))
  );
});
