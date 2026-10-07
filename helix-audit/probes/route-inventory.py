import os,sys,inspect,json,ast,pathlib
sys.path.insert(0,os.getcwd())
from app.main import app
rows=[]
def walk(routes,prefix='',inherited=[]):
 for r in routes:
  if hasattr(r,'dependant'):
   deps=[]
   def collect(d):
    for x in d.dependencies:
     deps.append(getattr(x.call,'__name__',str(x.call)));collect(x)
   collect(r.dependant)
   f=inspect.getsourcefile(r.endpoint)
   rows.append({'path':prefix+r.path,'methods':sorted(r.methods),'file':str(pathlib.Path(f).relative_to(pathlib.Path(os.getcwd()).parent)) if f and '/backend/' in f else f,'line':inspect.getsourcelines(r.endpoint)[1],'dependencies':sorted(set(deps))})
  elif hasattr(r,'routes'):walk(r.routes,prefix+getattr(r,'path',''))
  elif hasattr(r,'original_router'):walk(r.original_router.routes,prefix+r.include_context.prefix)
walk(app.routes)
# installed FastAPI's lazy include stores its effective routes on app.openapi paths;
# use operation IDs to associate method names if wrappers prevented introspection.
print('rows',len(rows),'openapi_paths',len(app.openapi()['paths']))
open('/home/vercel-sandbox/workspace/output/helix-audit/routes.json','w').write(json.dumps(rows,indent=2))
for r in rows:
 if not any(x in r['dependencies'] for x in ['get_current_user','get_current_admin','get_current_full_admin','get_current_active_user']):print(r)
