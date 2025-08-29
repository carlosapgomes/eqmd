// EquipeMed Service Worker - Static Assets Only
// Medical data always fetched fresh from server

const CACHE_NAME = 'eqmd-static-v1';
const STATIC_ASSETS = [
  '/',
  '/static/main.css',
  '/static/js/bootstrap.min.js',
  '/static/js/popper.min.js',
  '/static/css/bootstrap-icons.min.css',
  '/static/images/logo.png',
  '/static/manifest.json'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('PWA: Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .catch((error) => {
        console.log('PWA: Cache install failed:', error);
      })
  );
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('PWA: Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch event - serve from cache for static assets, network for medical data
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  // Never cache medical/patient data - always fetch fresh
  if (url.pathname.includes('/api/') || 
      url.pathname.includes('/patients/') ||
      url.pathname.includes('/events/') ||
      url.pathname.includes('/dailynotes/') ||
      url.pathname.includes('/mediafiles/') ||
      url.pathname.includes('/admin/') ||
      event.request.method !== 'GET') {
    return fetch(event.request);
  }
  
  // Cache-first strategy for static assets
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        if (response) {
          return response;
        }
        
        return fetch(event.request).then((response) => {
          // Only cache successful responses for static assets
          if (response.status === 200 && 
              (url.pathname.startsWith('/static/') || 
               url.pathname === '/' ||
               url.pathname.includes('.css') ||
               url.pathname.includes('.js') ||
               url.pathname.includes('.png') ||
               url.pathname.includes('.jpg') ||
               url.pathname.includes('.ico'))) {
            
            const responseClone = response.clone();
            caches.open(CACHE_NAME)
              .then((cache) => {
                cache.put(event.request, responseClone);
              });
          }
          
          return response;
        });
      })
      .catch(() => {
        // Fallback for offline - return cached version or error page
        if (event.request.destination === 'document') {
          return caches.match('/');
        }
      })
  );
});

// Handle install prompt
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});