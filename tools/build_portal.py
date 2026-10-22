import json,os,re,base64,hashlib,secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import sys
# usage: python3 build_portal.py PRIVATE_DIR REPO_DIR
# PRIVATE_DIR holds site/index.html (private portal page), portal_data.json, site/*.jpg, build/codes.json — never commit it
S=sys.argv[1]
REPO=sys.argv[2]
src=open(S+'/site/index.html').read()
data=json.load(open(S+'/portal_data.json'))
codes_path=S+'/build/codes.json'
if os.path.exists(codes_path): codes=json.load(open(codes_path))
else:
  al='abcdefghjkmnpqrstuvwxyz23456789'
  codes={u:'elk-'+'-'.join(''.join(secrets.choice(al) for _ in range(4)) for _ in range(3)) for u in data['INVESTORS']}
  json.dump(codes,open(codes_path,'w'))
ITER=250000
def enc(obj,code):
  salt=secrets.token_bytes(16);iv=secrets.token_bytes(12)
  key=PBKDF2HMAC(algorithm=hashes.SHA256(),length=32,salt=salt,iterations=ITER).derive(code.encode())
  ct=AESGCM(key).encrypt(iv,json.dumps(obj,separators=(',',':')).encode(),None)
  b=lambda x:base64.b64encode(x).decode()
  return {"v":1,"iter":ITER,"salt":b(salt),"iv":b(iv),"ct":b(ct)}
def fname(u): return hashlib.sha256(('elk:'+u).encode()).hexdigest()
imgs={}
for k in ['inspo','aerial','water','row','plan']:
  imgs[k]='data:image/jpeg;base64,'+base64.b64encode(open(S+f'/site/{k}.jpg','rb').read()).decode()
os.makedirs(REPO+'/portal/vault',exist_ok=True)
for f in os.listdir(REPO+'/portal/vault'): os.remove(REPO+'/portal/vault/'+f)
for u,inv in data['INVESTORS'].items():
  deals={k:data['DEALS'][k] for k in inv.get('holdings',{})}
  ex=data['EXAMPLES'] if inv.get('other') else {}
  payload={"investor":inv,"deals":deals,"examples":ex,"images":imgs if deals else {}}
  json.dump(enc(payload,codes[u]),open(REPO+f'/portal/vault/{fname(u)}.json','w'))
# public market prices (no amounts)
json.dump(data['PRICES'],open(REPO+'/prices.json','w'),indent=0)
# portal page
i=src.index('<script>');j=src.index('</script>',i)
js=src[i+8:j]
html=src[:i]

def cutblock(s,marker):
  a=s.index(marker);b=s.index('\n};\n',a);return s[:a]+marker+'};\n'+s[b+4:]
js=js.replace(js[js.index('const IMG='):js.index(';\n',js.index('const IMG='))],'const IMG={}')
js=cutblock(js,'const DEALS={')
js=cutblock(js,'const INVESTORS={')
a=js.index('const EXAMPLES=');b=js.index(';\n',a);js=js[:a]+'const EXAMPLES={}'+js[b:]
a=js.index('/*PRICES_START*/')+16;b=js.index('/*PRICES_END*/');js=js[:a]+'{"asof":"","buyDate":"","t":{}}'+js[b:]
# router: public pages live on the main site
js=js.replace('(()=>{const h=(location.hash||"").slice(1);go(PAGE_OF[h]||"home",h||undefined)})();','(()=>{const h=(location.hash||"").slice(1);go(h==="login"?"login":(PAGE_OF[h]||"home"),h&&h!=="login"?h:undefined)})();')

# scrub deal-specific text from public JS; it now comes from each partner's encrypted data
R=[('"Beach 5th & 6th Street · healthcare deal (~$12M) under review":"Healthcare deal (~$12M) under review · nothing invested"',
    'o.merged.map(id=>DEALS[id].name).join(" · ")+" · "+(o.pipelineShort||"deal under review"):(o.pipelineShort||"deal under review")+" · nothing invested"'),
   ('<b>Healthcare business acquisition</b><small>About $12,000,000 · diligence and terms in progress</small>','<b>${o.pipelineName||"Deal under review"}</b><small>${o.pipelineDetail||""}</small>'),
   ('"Beach 5th & 6th Street, at cost"','o.merged.map(id=>DEALS[id].name).join(", ")+", at cost"'),
   ('<b>~$12,000,000</b><em>healthcare business acquisition</em>','<b>${o.pipelineSize||"—"}</b><em>${(o.pipelineName||"").toLowerCase()}</em>'),
   ('${h.share===.5?"David Hillel":"Khezrie side"} · Block 15609','${session.name} · ${d.size}'),
   ('/* Beach 5th & 6th: figures from the Sept 2026 deal overview + GC term sheet */',''),
   ("/* Folds a partner's named deal into an undisclosed position (e.g. Beach 5th inside Eddie's real estate position) */","/* Folds a partner's named deal into one of their positions */"),
   ('" · 9 new homes, Far Rockaway (hands-on, at cost)"','" · "+d.type+", "+d.city.split(",")[0]+" (hands-on, at cost)"')]
for a_,c_ in R:
  assert a_ in js,a_[:50]; js=js.replace(a_,c_)
for o in data['INVESTORS']['eddie']['other']:
  if o.get('pipeline'):
    o.update(pipelineName="Healthcare business acquisition",pipelineDetail="About $12,000,000 · diligence and terms in progress",pipelineSize="~$12,000,000",pipelineShort="healthcare deal (~$12M) under review")
# login
a=js.index('/* Login */');b=js.index('/* Investor room */')
login='''/* Login: each partner's data is encrypted with their own code (PBKDF2 + AES-GCM). Nothing is readable without it. */
const codeEl=document.getElementById("code");
const b64=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
async function unlock(name,code){
  const h=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode("elk:"+name)))).map(x=>x.toString(16).padStart(2,"0")).join("");
  const r=await fetch("portal/vault/"+h+".json",{cache:"no-store"});if(!r.ok)throw new Error("nouser");
  const v=await r.json();
  const km=await crypto.subtle.importKey("raw",new TextEncoder().encode(code),"PBKDF2",false,["deriveKey"]);
  const key=await crypto.subtle.deriveKey({name:"PBKDF2",salt:b64(v.salt),iterations:v.iter,hash:"SHA-256"},km,{name:"AES-GCM",length:256},false,["decrypt"]);
  const pt=await crypto.subtle.decrypt({name:"AES-GCM",iv:b64(v.iv)},key,b64(v.ct));
  return JSON.parse(new TextDecoder().decode(pt));
}
document.getElementById("loginForm").addEventListener("submit",async e=>{
  e.preventDefault();
  const em=document.getElementById("email").value.trim().toLowerCase(),pin=codeEl.value.trim().toLowerCase();
  const err=document.getElementById("loginErr"),btn=e.target.querySelector("button[type=submit]");
  if(!em||!pin){err.textContent="Enter your login and your code.";return}
  err.textContent="Signing in…";btn.disabled=true;
  try{
    const p=await unlock(em,pin);
    Object.assign(DEALS,p.deals||{});Object.assign(EXAMPLES,p.examples||{});Object.assign(IMG,p.images||{});
    try{const pr=await (await fetch("prices.json",{cache:"no-store"})).json();Object.assign(PRICES,pr)}catch(x){}
    err.textContent="";session=p.investor;openRoom();
  }catch(x){err.textContent="That login and code don't match. Check both and try again.";codeEl.value="";codeEl.focus()}
  finally{btn.disabled=false}
});
document.getElementById("logout").addEventListener("click",()=>{location.reload()});

'''
js=js[:a]+login+js[b:]
doc='<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n<meta name="description" content="ELK Holdings is a family office investing across real estate, fixed income, private equity, venture capital, operating businesses, service and trade businesses and public equities.">\n<link rel="icon" href="crest-icon.jpg">\n<link rel="manifest" href="manifest.webmanifest">\n<meta name="theme-color" content="#000000">\n<link rel="apple-touch-icon" href="apple-touch-icon.png">\n<meta name="apple-mobile-web-app-capable" content="yes">\n<meta name="mobile-web-app-capable" content="yes">\n<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">\n<meta name="apple-mobile-web-app-title" content="ELK">\n'
k=html.index('\n<header')
out=doc+html[:k]+'\n</head>\n<body>\n'+html[k:]+'<script>'+js+'</script>\n<script>if("serviceWorker" in navigator)navigator.serviceWorker.register("sw.js",{scope:"./"}).catch(()=>{});</script>\n</body></html>\n'
open(REPO+'/index.html','w').write(out)
open(REPO+'/portal/index.html','w').write('<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=../#login"><title>ELK Holdings</title></head><body><a href="../#login">Investor login</a></body></html>\n')
for u,inv in data['INVESTORS'].items():
  deals={k:data['DEALS'][k] for k in inv.get('holdings',{})}
  ex=data['EXAMPLES'] if inv.get('other') else {}
  json.dump(enc({"investor":inv,"deals":deals,"examples":ex,"images":imgs if deals else {}},codes[u]),open(REPO+f'/portal/vault/{fname(u)}.json','w'))
print('built',len(out))
