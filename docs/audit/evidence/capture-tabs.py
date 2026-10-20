"""Read-only route/tab interaction captures; never submit provider or mutation forms."""
import sys,json,time,pathlib,re
sys.path.insert(0,str(pathlib.Path(__file__).parent))
from importlib.machinery import SourceFileLoader
c=SourceFileLoader('capture',str(pathlib.Path(__file__).with_name('capture-browser.py'))).load_module()

def open_page(path,lang):
 c.set_locale(lang);c.browser('open',c.BASE+path)
 try:c.browser('wait','--load','networkidle',timeout=28)
 except Exception:pass

def click_label(label):
 code='''(()=>{const label=LABEL;const buttons=[...document.querySelectorAll('button')];const b=buttons.find(x=>x.textContent.trim()===label)||buttons.find(x=>x.textContent.trim().startsWith(label));if(!b)return {clicked:false,available:buttons.map(x=>x.textContent.trim())};b.click();return {clicked:true,label:b.textContent.trim()}})()'''.replace('LABEL',json.dumps(label))
 return c.ev(code)

def shot(path,lang,name,extra=None):
 key=re.sub(r'[^a-zA-Z0-9]+','-',path.strip('/')).strip('-') or 'landing'
 name=re.sub(r'[^a-zA-Z0-9]+','-',name).strip('-')
 target=c.OUT/f'{key}-tab-{name}-{lang}.png'
 time.sleep(.25)
 state=c.ev('({path:location.pathname,lang:document.documentElement.lang,dir:document.documentElement.dir,text:document.body.innerText.slice(0,16000),navigation:performance.getEntriesByType("navigation").map(n=>({responseMs:n.responseEnd,domMs:n.domContentLoadedEventEnd,loadMs:n.loadEventEnd}))})')
 image=json.loads(c.browser('screenshot','--json'));target.write_bytes(pathlib.Path(image['data']['path']).read_bytes())
 row={'path':path,'locale':lang,'variant':'tab-'+name,'ok':True,'screenshot':'screens/'+target.name,'state':state,'interaction':extra}
 with c.LOG.open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
 print(path,lang,name,extra,flush=True)

plans={
 '/notifications':['All','Unread','Announcements','Alerts'],
 '/create':['Image Creative','Video Motion'],
 '/scout/social':['Active Workspace','Org Social Jobs','Org Maps Jobs'],
 '/scout/maps':['Active Workspace','Org Social Jobs','Org Maps Jobs'],
 '/guide':['Helix Architecture & The 4 Loops','Discover — Competitor Ad Extraction','Intelligence — Pattern Synthesis & Teardowns','Create Studio — AI Generation','Performance — Longevity & Fatigue Tracking','Admin Center & Operations'],
 '/admin/guide':['Helix Architecture & The 4 Loops','Discover — Competitor Ad Extraction','Intelligence — Pattern Synthesis & Teardowns','Create Studio — AI Generation','Performance — Longevity & Fatigue Tracking','Admin Center & Operations'],
 '/admin/support':['All Types','All Statuses'],
}
for lang in ['en','ar']:
 for path,labels in plans.items():
  try:
   open_page(path,lang)
   for label in labels:
    result=click_label(label)
    if not result.get('clicked') and path.endswith('/guide'):
     result=c.ev('''(()=>{const target=LABEL;const b=[...document.querySelectorAll('button')].find(x=>x.innerText.includes(target));if(!b)return {clicked:false};b.click();return {clicked:true}})()'''.replace('LABEL',json.dumps(label.split(' — ')[0])))
    shot(path,lang,label,result)
  except Exception as exc:print('ERROR',path,lang,str(exc)[:800],flush=True)
 # The editor opens a local unsaved modal. No save/publish action is performed.
 try:
  open_page('/admin/updates',lang)
  opened=click_label('New Update');shot('/admin/updates',lang,'new-editor',opened)
  viewed=click_label('Preview');shot('/admin/updates',lang,'preview',viewed)
  viewed=click_label('Editor');shot('/admin/updates',lang,'editor',viewed)
 except Exception as exc:print('ERROR updates',lang,str(exc),flush=True)
 # Filter options are view-only; there are no result records in this database.
 try:
  open_page('/performance',lang)
  selects=c.ev('[...document.querySelectorAll("select")].map((s,i)=>({index:i,options:[...s.options].map(o=>({value:o.value,label:o.textContent}))}))')
  for field in selects:
   for option in field['options']:
    c.ev('''(()=>{const s=document.querySelectorAll('select')[INDEX];s.value=VALUE;s.dispatchEvent(new Event('change',{bubbles:true}));return true})()'''.replace('INDEX',str(field['index'])).replace('VALUE',json.dumps(option['value'])))
    shot('/performance',lang,'filter-'+option['label'],{'selected':option})
 except Exception as exc:print('ERROR performance',lang,str(exc),flush=True)
 # API keys loads through SPA navigation, unlike the conflicting /api dev proxy on direct load.
 try:
  open_page('/discover',lang)
  c.browser('click','a[href="/api-keys"]');c.browser('wait','--load','networkidle',timeout=28)
  shot('/api-keys',lang,'spa-navigation',{'entry':'sidebar-link'})
 except Exception as exc:print('ERROR api-keys',lang,str(exc),flush=True)
 # Capture final async empty states, separate from initial loading evidence.
 for path in ['/dashboard','/admin','/admin/usage']:
  try:open_page(path,lang);shot(path,lang,'settled',{'wait':'networkidle bounded 28s'})
  except Exception as exc:print('ERROR settled',path,lang,str(exc),flush=True)
