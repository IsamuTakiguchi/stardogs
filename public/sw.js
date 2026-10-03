// STAR DOGS service worker: precache the game so it starts offline, refresh in the background.
const VERSION = 'stardogs-v1';
const SHELL = [
  './',
  'index.html',
  'manifest.webmanifest?v=2',
  'vendor/three.min.js',
  'vendor/CopyShader.js',
  'vendor/LuminosityHighPassShader.js',
  'vendor/EffectComposer.js',
  'vendor/RenderPass.js',
  'vendor/ShaderPass.js',
  'vendor/UnrealBloomPass.js',
  'icons/icon-192.png?v=2',
  'icons/icon-512.png?v=2',
  'icons/icon-maskable-192.png?v=2',
  'icons/icon-maskable-512.png?v=2',
  'icons/apple-touch-icon.png?v=2',
  'icons/apple-touch-icon-167.png?v=2',
  'icons/apple-touch-icon-152.png?v=2',
  'icons/favicon-32.png?v=2',
];
const FONT_HOSTS = ['fonts.googleapis.com', 'fonts.gstatic.com'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  const sameOrigin = url.origin === self.location.origin;
  if (!sameOrigin && !FONT_HOSTS.includes(url.hostname)) return;

  // Pages: network first so a new deploy shows up, cached copy when offline.
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req)
        .then((res) => { const copy = res.clone(); caches.open(VERSION).then((c) => c.put('index.html', copy)); return res; })
        .catch(() => caches.match('index.html'))
    );
    return;
  }
  // Everything else: cache first, update in the background.
  e.respondWith(
    caches.match(req).then((hit) => {
      const net = fetch(req)
        .then((res) => { if (res.ok || res.type === 'opaque') { const copy = res.clone(); caches.open(VERSION).then((c) => c.put(req, copy)); } return res; })
        .catch(() => hit);
      return hit || net;
    })
  );
});
