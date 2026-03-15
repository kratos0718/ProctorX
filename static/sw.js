/* ProctorX Service Worker — enables PWA install + offline shell */
const CACHE = 'proctorx-v1';
const PRECACHE = [
  '/',
  '/static/manifest.json',
  'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap',
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  // Network-first for API calls and dynamic pages
  if (e.request.url.includes('/api/') ||
      e.request.url.includes('/proctor/') ||
      e.request.url.includes('/exam/') ||
      e.request.url.includes('/code') ||
      e.request.method !== 'GET') {
    return; // let browser handle it
  }

  e.respondWith(
    fetch(e.request)
      .then(resp => {
        const clone = resp.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
        return resp;
      })
      .catch(() => caches.match(e.request))
  );
});
