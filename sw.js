
const CACHE_NAME = "strike-wall-v1";

const APP_SHELL = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./icon-192.png",
  "./icon-512.png"
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys
          .filter(key => key !== CACHE_NAME)
          .map(key => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  const request = event.request;
  const url = new URL(request.url);

  if (request.method !== "GET" ||
      url.origin !== self.location.origin) return;

  if (url.pathname.endsWith("/data/spx_daily.csv")) {
    event.respondWith(
      fetch(request)
        .then(response => {
          if (response.ok) {
            const copy = response.clone();
            const cleanRequest = new Request(
              url.origin + url.pathname
            );

            caches.open(CACHE_NAME)
              .then(cache => cache.put(cleanRequest, copy));
          }
          return response;
        })
        .catch(async () => {
          const cleanRequest = new Request(
            url.origin + url.pathname
          );

          return await caches.match(cleanRequest) ||
            new Response(
              "Datos del SPX no disponibles sin conexión.",
              { status: 503 }
            );
        })
    );
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then(response => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME)
              .then(cache => cache.put("./", copy));
          }
          return response;
        })
        .catch(async () => {
          return await caches.match("./") ||
                 await caches.match("./index.html");
        })
    );
  }
});
