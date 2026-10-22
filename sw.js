// ELK Holdings app: keeps the site shell available offline. Partner data and prices always come from the network.
const CACHE="elk-v1";
const SHELL=["./","index.html","crest.jpg","crest-icon.jpg","crest-head.jpg","icon-192.png","icon-512.png","portal/","portal/index.html"];
self.addEventListener("install",e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()))});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==CACHE).map(x=>caches.delete(x)))).then(()=>self.clients.claim()))});
self.addEventListener("fetch",e=>{
  const u=new URL(e.request.url);
  if(e.request.method!=="GET"||u.origin!==location.origin)return;
  if(u.pathname.includes("/vault/")||u.pathname.endsWith("prices.json"))return; // never cache partner data or prices
  e.respondWith(fetch(e.request).then(r=>{const c=r.clone();caches.open(CACHE).then(x=>x.put(e.request,c));return r}).catch(()=>caches.match(e.request)));
});
