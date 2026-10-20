"""Capture local audited routes without mocked responses or provider submissions."""
import json,subprocess,time,pathlib,re,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'screens';OUT.mkdir(exist_ok=True)
LOG=ROOT/'evidence/browser-captures.jsonl'
BASE='http://127.0.0.1:3000'
def browser(*args,timeout=35):
 r=subprocess.run(['agent-browser',*args],capture_output=True,text=True,timeout=timeout)
 if r.returncode: raise RuntimeError(r.stdout[:1000]+r.stderr[:500])
 return r.stdout.strip()
def ev(code):
 raw=json.loads(browser('eval','--json',code))
 if not raw.get('success'):raise RuntimeError(str(raw))
 return raw['data'].get('result')
def capture(path,lang,variant='route',selector=None):
 key=re.sub(r'[^a-zA-Z0-9]+','-',path.strip('/')).strip('-') or 'landing'
 suffix='' if variant=='route' else '-'+re.sub(r'[^a-zA-Z0-9]+','-',variant).strip('-')
 target=OUT/f'{key}{suffix}-{lang}.png'
 item={'path':path,'locale':lang,'variant':variant,'screenshot':'screens/'+target.name}
 start=time.monotonic()
 try:
  browser('open',BASE+path)
  # Read the actual DOM until the async route either renders or settles on fallback.
  for _ in range(40):
   state=ev('({ready:document.readyState,text:document.body.innerText,dir:document.documentElement.dir,lang:document.documentElement.lang,path:location.pathname,query:location.search})')
   if state and len(state.get('text','').strip())>30 and not re.fullmatch(r'[⏳\s]*(Loading|جاري التحميل|جارٍ التحميل).*',state['text'].strip()):break
   time.sleep(.2)
  if selector:
   browser('click',selector)
   time.sleep(.15)
  item['loadMs']=round((time.monotonic()-start)*1000)
  item['state']=ev('({title:document.title,path:location.pathname,query:location.search,lang:document.documentElement.lang,dir:document.documentElement.dir,text:document.body.innerText.slice(0,16000),headings:[...document.querySelectorAll("h1,h2,h3")].map(x=>x.textContent),tabs:[...document.querySelectorAll("[role=tab]")].map(x=>({text:x.textContent,selected:x.getAttribute("aria-selected")})),buttons:[...document.querySelectorAll("button")].map(x=>({text:x.textContent,aria:x.getAttribute("aria-label"),disabled:x.disabled}))})')
  shot=json.loads(browser('screenshot','--json'))
  data=pathlib.Path(shot['data']['path']).read_bytes();target.write_bytes(data)
  item['bytes']=len(data);item['ok']=True
 except Exception as e:item['ok']=False;item['error']=str(e)[:1600]
 with LOG.open('a') as f:f.write(json.dumps(item,ensure_ascii=False)+'\n')
 print(json.dumps({k:v for k,v in item.items() if k!='state'},ensure_ascii=False),flush=True)
 return item

def set_locale(lang):
 ev('localStorage.setItem("helix_lang",'+json.dumps(lang)+');true')

if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='public':
  routes=['/','/sign-in','/sign-up','/forgot-password','/reset-password','/legal','/legal/privacy','/privacy','/terms','/cookies','/updates','/playbook/audit-not-found','/docs','/docs/scout-cli','/docs/user-guide','/docs/api-reference']
  registry=pathlib.Path('src/features/docs/docsData.js').read_text();section=None
  for line in registry.splitlines():
   m=re.search(r"section: '([^']+)'",line)
   if m:section=m.group(1)
   m=re.search(r"slug: '([^']+)'",line)
   if m and section:routes.append('/docs/'+section+'/'+m.group(1))
 elif mode=='protected':
  routes=['/discover','/intelligence','/create','/performance','/monitors','/scout','/scout/social','/scout/maps','/scout/lead-generation','/swipe-files','/dashboard','/guide','/billing','/api-keys','/team','/team/accept','/settings','/support','/notifications','/not-a-real-route']
  routes+=re.findall(r'path: "([^"]+)"',pathlib.Path('src/app/admin/adminNavigation.js').read_text())
 else:routes=sys.argv[2:]
 for lang in ['en','ar']:
  set_locale(lang)
  for path in routes:capture(path,lang)
