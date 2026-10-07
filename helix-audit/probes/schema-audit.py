import os,sys,asyncio,json,inspect as pyinspect
sys.path.insert(0,os.getcwd())
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.dialects import postgresql
from app.models import Base
import app.models
out='/home/vercel-sandbox/workspace/output/helix-audit'
def column(c):
 return {'type':str(c.type.compile(dialect=postgresql.dialect())), 'nullable':c.nullable, 'server_default':str(c.server_default.arg) if c.server_default is not None else None,'python_default':str(c.default.arg) if c.default is not None and not c.default.is_callable else ('callable' if c.default else None),'foreign_keys':sorted(f.target_fullname for f in c.foreign_keys)}
def compare(conn):
 i=inspect(conn); dbtables=set(i.get_table_names()); inventory={}; mismatches=[]
 for name,t in sorted(Base.metadata.tables.items()):
  model={c.name:column(c) for c in t.columns}; inventory[name]={'model':model,'model_indexes':[{'name':idx.name,'unique':idx.unique,'columns':[str(c) for c in idx.expressions]} for idx in t.indexes]}
  inventory[name]['model_constraints']=[{'kind':type(x).__name__,'name':x.name,'columns':[c.name for c in x.columns], 'definition':str(x)} for x in t.constraints]
  if name not in dbtables:
   mismatches.append({'table':name,'kind':'missing_table','columns':list(model)}); continue
  actual={c['name']:c for c in i.get_columns(name)}; inventory[name]['database_columns']={n:{**v,'type':str(v['type'])} for n,v in actual.items()};inventory[name]['database_indexes']=i.get_indexes(name)
  for n,c in model.items():
   if n not in actual: mismatches.append({'table':name,'column':n,'kind':'missing_column',**c}); continue
   a=actual[n]
   if c['nullable'] != a['nullable']: mismatches.append({'table':name,'column':n,'kind':'nullability','model':c['nullable'],'migration':a['nullable']})
   # compare Alembic types with dialect's comparison to suppress synonyms
   from alembic.migration import MigrationContext
   from sqlalchemy import Column
   if MigrationContext.configure(conn).impl.compare_type(Column(n,a['type']),t.c[n]): mismatches.append({'table':name,'column':n,'kind':'type','model':c['type'],'migration':str(a['type'])})
   if bool(c['server_default']) != bool(a['default']): mismatches.append({'table':name,'column':n,'kind':'server_default','model':c['server_default'],'migration':a['default'],'python_default':c['python_default']})
  for n in actual.keys()-model.keys(): mismatches.append({'table':name,'column':n,'kind':'extra_column'})
  dbidx={x['name']:x for x in i.get_indexes(name)}
  for ix in t.indexes:
   if ix.name not in dbidx:mismatches.append({'table':name,'kind':'missing_index','name':ix.name,'columns':[str(c) for c in ix.expressions]})
  for ix in dbidx.keys()-{x.name for x in t.indexes}:
   if not dbidx[ix].get('duplicates_constraint'): mismatches.append({'table':name,'kind':'extra_index','definition':dbidx[ix]})
  for ix in t.indexes:
   if ix.name in dbidx and (bool(ix.unique)!=bool(dbidx[ix.name]['unique']) or [c.name for c in ix.columns]!=dbidx[ix.name]['column_names']): mismatches.append({'table':name,'kind':'index_definition','name':ix.name})
  dbfk={(tuple(x['constrained_columns']),x['referred_table'],tuple(x['referred_columns'])) for x in i.get_foreign_keys(name)}
  mfk={(tuple(c.name for c in x.columns),x.referred_table.name,tuple(e.column.name for e in x.elements)) for x in t.foreign_key_constraints}
  for fk in mfk-dbfk: mismatches.append({'table':name,'kind':'missing_fk','definition':str(fk)})
  for fk in dbfk-mfk: mismatches.append({'table':name,'kind':'extra_fk','definition':str(fk)})
  from sqlalchemy import UniqueConstraint
  uq={tuple(x['column_names']) for x in i.get_unique_constraints(name)}; muq={tuple(c.name for c in x.columns) for x in t.constraints if isinstance(x,UniqueConstraint)}
  for x in muq-uq: mismatches.append({'table':name,'kind':'missing_unique','columns':x})
  for x in uq-muq: mismatches.append({'table':name,'kind':'extra_unique','columns':x})
 open(out+'/schema-inventory.json','w').write(json.dumps(inventory,indent=2,default=str));open(out+'/schema-mismatches.json','w').write(json.dumps(mismatches,indent=2,default=str))
 from collections import Counter
 print('Model tables',len(inventory),'migration tables',len(dbtables)-1,'mismatches',dict(Counter(m['kind'] for m in mismatches)))
 for m in mismatches:
  if m['kind']!='server_default': print(m)
async def main():
 e=create_async_engine(os.environ['DATABASE_URL'].replace('postgresql://','postgresql+asyncpg://'))
 async with e.connect() as c:await c.run_sync(compare)
 await e.dispose()
asyncio.run(main())
