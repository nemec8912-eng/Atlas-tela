// Атлас тела: офлайн-кэш. Модели и код кэшируются при первом открытии.
const CACHE='atlas-tela-v7';
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(['./','./index.html','./app.js','./app.css','./models/atlas.json','./favicon.svg','./manifest.webmanifest']).catch(()=>{})));self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==CACHE).map(x=>caches.delete(x)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{
  const r=e.request;if(r.method!=='GET'||new URL(r.url).origin!==location.origin)return;
  const isModel=r.url.includes('/models/geo-');
  e.respondWith(caches.open(CACHE).then(async c=>{
    const hit=await c.match(r);
    if(hit&&isModel)return hit; // геометрия не меняется в пределах версии
    try{const res=await fetch(r);if(res.ok)c.put(r,res.clone());return res;}catch(err){if(hit)return hit;throw err;}
  }));
});
