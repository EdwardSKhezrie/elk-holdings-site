// ELK Holdings app: keeps the site shell available offline. Partner data and prices always come from the network.
const CACHE="elk-v20";
const SHELL=["./","index.html","crest.jpg","crest-icon.jpg","crest-head.jpg","icon-192.png","icon-512.png","portal/","portal/index.html","app/","app/index.html","partners/","partners/index.html"];
self.addEventListener("install",e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()))});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==CACHE).map(x=>caches.delete(x)))).then(()=>self.clients.claim()))});
self.addEventListener("fetch",e=>{
  const u=new URL(e.request.url);
  if(e.request.method!=="GET"||u.origin!==location.origin)return;
  if(u.pathname.includes("/vault/")||u.pathname.includes("/portal/docs/")||/(prices|history)(\.enc)?\.json$/.test(u.pathname))return; // never cache partner data or prices
  const fresh=e.request.mode==="navigate"||u.pathname.endsWith(".html")||u.pathname.endsWith("/");
  e.respondWith(fetch(e.request,fresh?{cache:"no-store"}:{}).then(r=>{const c=r.clone();caches.open(CACHE).then(x=>x.put(e.request,c));return r}).catch(()=>caches.match(e.request)));
});
