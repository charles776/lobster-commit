// Force immediate update - skip waiting, claim all clients
self.addEventListener('install', e => { self.skipWaiting(); });
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k))))
  );
  e.waitUntil(clients.claim());
});

// Network-first with cache fallback
self.addEventListener('fetch', e => {
  e.respondWith(
    fetch(e.request).then(resp => {
      const clone = resp.clone();
      caches.open('commit-v8').then(c => c.put(e.request, clone));
      return resp;
    }).catch(() => caches.match(e.request))
  );
});
