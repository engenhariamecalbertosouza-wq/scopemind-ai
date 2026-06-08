// Service worker do ScopeMind AI (deixa o app instalável e funcional offline parcialmente).
const CACHE = "scopemind-v8";
const SHELL = ["/", "/index.html", "/styles.css", "/app.js", "/cerebro.html", "/manifest.json", "/icon-192.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  // Apaga caches de versões antigas (garante que todos peguem a versão nova).
  e.waitUntil(
    caches.keys().then((nomes) =>
      Promise.all(nomes.filter((n) => n !== CACHE).map((n) => caches.delete(n)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  // Nunca usar cache para a API — dados sempre frescos.
  if (url.pathname.startsWith("/api/")) return;
  // Rede primeiro; se cair (offline), usa o cache.
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});
