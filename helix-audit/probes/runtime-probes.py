import asyncio,os,sys,inspect,json,datetime,types,io
sys.path.insert(0,os.getcwd())
from sqlalchemy import select,text
from app.db.session import engine,async_session_maker
from app.models import Base
from app.models.user import User
from app.models.organization import Organization
from app.models.plan import Plan
from app.models.scrape_job import ScrapeJob
from app.models.creative import Creative
from app.models.pattern import Pattern
from app.models.ai_insight import AIInsight
from app.core.security import get_password_hash,create_access_token,verify_password
from app.main import app
import httpx
async def main():
 async with engine.begin() as c:await c.run_sync(Base.metadata.create_all)
 now=datetime.datetime.now(datetime.timezone.utc)
 async with async_session_maker() as db:
  db.add_all([User(id='alice',email='alice@example.com',password_hash='EXTERNAL_AUTH_MANAGED',trial_expires_at=now+datetime.timedelta(days=7)),User(id='bob',email='bob@example.com',password_hash=get_password_hash('BobSynthetic123!'),trial_expires_at=now+datetime.timedelta(days=7))]);await db.flush()
  db.add(Plan(id='plan_trial_default',name='trial',type='trial',daily_credit_limit=100,feature_flags={'swipe_files':True}));db.add_all([Organization(id='oa',name='Alice',owner_id='alice',credit_balance=25),Organization(id='ob',name='Bob',owner_id='bob',credit_balance=25)]);await db.flush()
  db.add(ScrapeJob(id='private-job',org_id='oa',query='secret-campaign',status='succeeded',created_at=now));await db.flush()
  db.add(Creative(id='private-creative',job_id='private-job',brand_id='private-brand',brand_name='Secret Brand',platform='meta',format='image',headline='Alice private strategy',body='Confidential campaign draft'));db.add(Pattern(id='private-pattern',job_id='private-job',label='Alice secret pattern',family='copy',prevalence=.5,lift_index=1.2));await db.flush();db.add(AIInsight(id='private-insight',creative_id='private-creative',kind='opportunity',title='Private insight',summary='Private strategic summary',confidence=.9));await db.commit()
 async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,raise_app_exceptions=False),base_url='http://local') as c:
  r=await c.post('/api/auth/sign-in',json={'email':'alice@example.com','password':'EXTERNAL_AUTH_MANAGED'});print('sentinel_login',r.status_code,'token_issued',bool(r.json().get('access_token')))
  headers={'Authorization':'Bearer '+create_access_token('bob')}
  for path in ['/api/creatives/private-creative','/api/brands/','/api/patterns/']:
   r=await c.get(path,headers=headers);print(path,r.status_code,'private_data',any(s in r.text for s in ['Secret Brand','Alice secret pattern']))
  r=await c.post('/api/creatives/private-creative/save',headers=headers);print('save_foreign',r.status_code)
  r=await c.get('/api/creatives/saved',headers=headers);print('saved_foreign_content',r.status_code,'Alice private strategy' in r.text)
  r=await c.post('/api/playbooks',headers=headers,json={'brand_name':'x','query':'x','job_id':'private-job'});print('compile_foreign',r.status_code)
  if r.status_code==200:
   r=await c.get('/api/playbooks/public/'+r.json()['public_id']);print('public_foreign_content',r.status_code,'Alice private strategy' in r.text)
  r=await c.post('/api/account/avatar',headers=headers,files={'file':('avatar.png',b'synthetic','image/png')});print('avatar_upload',r.status_code)
  r=await c.post('/api/creatives/custom',headers=headers,json={'url':'https://example.com'});print('custom_swipe',r.status_code)
  r=await c.post('/api/creatives/private-creative/generate-insights',headers=headers);print('managed_insight_with_defaults',r.status_code)
 from app.services.ai.ai_router import MultiTierAIProvider
 try: MultiTierAIProvider(); print('multitier_init_ok')
 except Exception as e:print('multitier_init',type(e).__name__,str(e))
 from app.services.ai.gemini_provider import GeminiProvider
 try: inspect.signature(GeminiProvider.generate_image).bind(None,prompt='x',reference_images=[],aspect_ratio='1:1',seed=None)
 except TypeError as e:print('gemini_invocation',str(e))
 from app.services.security_service import is_safe_public_url
 print('mapped_loopback_accepted',is_safe_public_url('http://[::ffff:127.0.0.1]/'))
 from app.services import billing_service
 async with async_session_maker() as db:
  await billing_service.refund(db,'ob',1,'probe','same-job');await billing_service.refund(db,'ob',1,'probe','same-job');org=await db.get(Organization,'ob');print('repeated_refund_balance',org.credit_balance)
 # demonstrate stale cached org even with FOR UPDATE after a concurrent commit
 async with async_session_maker() as db1,async_session_maker() as db2:
  u1=await db1.get(User,'bob');org1=await billing_service.get_or_create_default_org(db1,u1);await db1.commit()
  u2=await db2.get(User,'bob');org2,_=await billing_service.assert_can_spend(db2,u2,required_credits=1);await billing_service.charge(db2,org2,'bob',1,'test','test')
  org1,_=await billing_service.assert_can_spend(db1,u1,required_credits=1);before=org1.credit_balance;await billing_service.charge(db1,org1,'bob',1,'test','test');print('cached_org_lock_balance_before',before,'after_two_charges',org1.credit_balance)
 await engine.dispose()
asyncio.run(main())
