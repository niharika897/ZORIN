// ZORIN Service Worker
const CACHE_NAME = 'zorin-cache-v1';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  // Let network handle all dynamic API requests directly
  if (event.request.url.includes('/api/') || event.request.url.includes('/ws/')) {
    return;
  }
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
