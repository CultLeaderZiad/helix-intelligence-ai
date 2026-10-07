import os,sys,asyncio,json
sys.path.insert(0,os.getcwd())
from sqlalchemy import inspect,UniqueConstraint
from sqlalchemy.ext.asyncio import create_async_engine
from app.models import Base
import app.models
out='/home/vercel-sandbox/workspace/output/helix-audit/schema-inventory.json'
def run(c):
 i=inspect(c);extra=[];inv=json.load(open(out))
 for n,t in Base.metadata.tables.items():
  fk=[{'columns':[x.name for x in q.columns],'target_table':q.referred_table.name,'target_columns':[e.column.name for e in q.elements],'ondelete':q.ondelete,'onupdate':q.onupdate,'deferrable':q.deferrable,'initially':q.initially} for q in t.foreign_key_constraints]
  inv[n]['model_foreign_keys']=fk
  if not i.has_table(n):continue
  dbfk=i.get_foreign_keys(n); inv[n]['database_foreign_keys']=dbfk;inv[n]['database_unique_constraints']=i.get_unique_constraints(n);inv[n]['database_primary_key']=i.get_pk_constraint(n)
  for m in fk:
   d=next((x for x in dbfk if x['constrained_columns']==m['columns'] and x['referred_table']==m['target_table']),None)
   if d:
    for k in ('ondelete','onupdate','deferrable','initially'):
     if (d.get('options',{}).get(k) or None)!=(m[k] or None):extra.append((n,'fkoption',k,m[k],d))
  if list(t.primary_key.columns.keys())!=i.get_pk_constraint(n)['constrained_columns']:extra.append((n,'pk'))
  for col in t.columns:
   a=inv[n].get('database_columns',{}).get(col.name,{})
   if col.server_default is not None and a.get('default') is not None:
    m=str(col.server_default.arg);d=a['default']
    if m.lower()!=d.lower():extra.append((n,col.name,'both_server_defaults',m,d))
 open(out,'w').write(json.dumps(inv,indent=2,default=str))
 print('additional_PK_FK_actions_existing_server_default_differences',extra)
async def main():
 e=create_async_engine(os.environ['DATABASE_URL'].replace('postgresql://','postgresql+asyncpg://'))
 async with e.connect() as c:await c.run_sync(run)
 await e.dispose()
asyncio.run(main())
