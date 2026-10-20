"""Build auditable indexes from the actual local capture records, not route guesses."""
import pathlib,json,re,statistics,collections
ROOT=pathlib.Path(__file__).resolve().parents[1]
rows=[json.loads(s) for s in (ROOT/'evidence/browser-captures.jsonl').read_text().splitlines()]
latest={(r['path'],r['locale'],r['variant']):r for r in rows}
valid=[r for r in latest.values() if r['ok'] and (ROOT/r['screenshot']).exists() and r.get('interaction',{}).get('clicked') is not False]
static=json.load(open(ROOT/'evidence/frontend-routes.json'))['routes']
def matched(path):
 for route in static:
  pattern=re.sub(r':[A-Za-z]+','[^/]+',route['path'])
  if re.fullmatch(pattern,path):return route
 return {}
def esc(s):return str(s).replace('|','\\|').replace('\n',' ')
paths=sorted({r['path'] for r in valid if r['variant']=='route'})
out=['# جرد الـbrowser الفعلي — EN / AR + RTL','',f'كود W4: `eab70cc`. **{len(paths)} concrete paths**، و**{sum(r["variant"]=="route" for r in valid)} route/locale screenshots**. إجمالي **{len(valid)} screenshots** صالحة موجودة؛ الـraw log فيه محاولات أقدم/غير متطابقة محفوظة للتتبّع مش counted كنجاح.','', 'البيانات من local empty/disposable DB، ومفيش provider output أو populated-detail records. Status الكود مش ضمان outcome؛ صورة loading مش terminal success. وصف `empty/partial` مش `mock` إلا لو config فعلًا mock، والـAPI هنا `USE_MOCKS=false`.','', 'لقطات التابات/الـmodes وpending access تحت جدول الصفحات. تفاصيل source/status في [FRONTEND-INVENTORY](FRONTEND-INVENTORY.md).','', '| Path | الوظيفة / المكونات | Status مرصود | Endpoints من source | EN | AR |','|---|---|---|---|---|---|']
by={(r['path'],r['locale'],r['variant']):r for r in valid}
for path in paths:
 route=matched(path);a=by.get((path,'en','route'));b=by.get((path,'ar','route'))
 state=(a or b)['state'];text=state.get('text','');status=route.get('status','partial')
 if path=='/api-keys':status='broken direct dev load; SPA partial/loaded'
 elif state.get('path')!=path:status='redirect → '+state.get('path','unknown')
 elif any(x in text.lower() for x in ['no data','no discovery','no notifications','no tickets','no updates','no monitor','empty','no scored','no timeline','no performance','no competitor','no scrape jobs']):status='empty / API outcome not provider-verified'
 elif any(x in text for x in ['Loading','LOADING','Initializing']):status='initial loading; see settled capture if available'
 elif path.startswith('/docs') or path in ['/legal','/privacy','/terms','/cookies','/legal/privacy','/guide','/admin/guide']:status='real static content; AR translation partial'
 def link(x):return f'[لقطة]({x["screenshot"]})' if x else 'not verified'
 purpose=route.get('purpose', 'المقالة المسجلة / route instance');comp=', '.join(route.get('keyComponents',[]));api='; '.join(route.get('apiCalls',[])) or 'static / shared auth+chrome calls'
 out.append(f'| `{path}` | {esc(purpose)} — `{esc(comp)}` | {esc(status)} | {esc(api)} | {link(a)} | {link(b)} |')
out+=['','## Tabs / modes / filters / access states','', 'دي الحالات اللي اتفتحت فعليًا. مجرد فتح form/editor من غير Save/Publish مش mutation proof. Detail tabs اللي محتاجة real record/provider output **not verified**؛ ما اتعملتش fake records عشان تتفتح.','', '| Route | الحالة | Interaction | EN | AR |','|---|---|---|---|---|']
groups=collections.defaultdict(dict)
for r in valid:
 if r['variant']!='route':groups[r['path'],r['variant']][r['locale']]=r
for (path,variant),langs in sorted(groups.items()):
 r=langs.get('en') or langs.get('ar');interaction=r.get('interaction',{});desc=interaction.get('label') or interaction.get('selected') or interaction.get('wait') or interaction.get('identity') or interaction.get('entry') or ('selected option' if 'selected' in interaction else 'view-only click')
 out.append(f'| `{path}` | `{variant}` | {esc(desc)} | '+('['+'لقطة]('+langs['en']['screenshot']+')' if 'en'in langs else 'not verified')+' | '+('['+'لقطة]('+langs['ar']['screenshot']+')' if 'ar'in langs else 'not verified')+' |')
nav=[]
for r in valid:
 for n in r.get('state',{}).get('navigation',[]):
  if n.get('loadMs',0)>0:nav.append(n)
out+=['','## توقيتات الـpreview وحدودها','', 'مافيش production قياس أو load test. `loadMs` في أعلى capture record يشمل CLI/انتظار/فحص DOM؛ مايتقالش عليه LCP أو page-load pure. الأرقام الجاية من browser Performance Navigation Timing فقط، على جهاز shared sandbox مع empty DB وdevelopment Vite، ومفيهاش ضمان API/provider completion.']
if nav:
 out.append(f'- عدد navigation timing samples الصالحة: **{len(nav)}** (فيهم repeated page loads؛ مش unique users).')
 for name in ['responseMs','domMs','loadMs']:
  vals=[n[name] for n in nav if n.get(name,0)>0]
  out.append(f'- `{name}`: min **{min(vals):.1f}ms**، median **{statistics.median(vals):.1f}ms**، max **{max(vals):.1f}ms**. ده descriptive للعينات دي بس، مش p95/SLO.')
out+=['','## Browser findings مؤكدة','', '- `/api-keys`: direct GET بيتحوّل للbackend بسبب dev proxy `/api` prefix؛ JSON404. Sidebar SPA entry فتح API-keys UI؛ production direct-load **not verified**.', '- pending account على Create بيشوف trial-ended/select-plan language رغم access pending. billing/access متداخلين.', '- `lang/dir` اتبدلوا EN→AR/RTL؛ docs/auth/admin/Create وغيرهم لسه بيعرضوا English. Screenshots دليل partial localization مش compliance.', '- dashboard/admin/usage عندهم initial skeletons ثم settled captures منفصلة؛ ما اتوصّفوش permanent hang من snapshot مبكر.', '- provider-dependent populated details، generation، إرسال emails/invites، published updates وreal lead/job details: **not verified**.']
(ROOT/'BROWSER-INVENTORY.md').write_text('\n'.join(out)+'\n')
index=['# Screenshots — لقطة لكل route وحالة متاحة','',f'**{len(valid)} PNG screenshots** من local managed preview. اللغات EN/AR، والبيانات الحقيقية الوحيدة هنا حسابات اختبار disposable محلية وempty/API states. مفيش customer data أو provider keys أو fake AI results.','', 'الفهرس الوظيفي الكامل: [BROWSER-INVENTORY](../BROWSER-INVENTORY.md). الصور بتثبت الحالة المرئية وقت الالتقاط بس؛ مش ضمان نجاح feature أو مزوّد.','', '| Route | Locale | State | Screenshot |','|---|---|---|---|']
for r in sorted(valid,key=lambda x:(x['path'],x['variant'],x['locale'])):
 index.append(f'| `{r["path"]}` | {r["locale"]} | `{r["variant"]}` | [{pathlib.Path(r["screenshot"]).name}]({pathlib.Path(r["screenshot"]).name}) |')
(ROOT/'screens/README.md').write_text('\n'.join(index)+'\n')
json.dump({'snapshot':'eab70cc75bbc2aa8fe841a2c792f72bfd8e7e957','concretePaths':len(paths),'routeLocaleScreenshots':sum(r['variant']=='route' for r in valid),'validScreenshotCount':len(valid),'rawAttempts':len(rows),'validCaptures':[{k:v for k,v in r.items() if k!='state'} for r in valid]},open(ROOT/'evidence/browser-summary.json','w'),ensure_ascii=False,indent=2)
print('Indexed',len(paths),'paths',len(valid),'valid screenshots;',len(rows),'raw attempts')
