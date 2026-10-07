import os,sys,asyncio
sys.path.insert(0,os.getcwd())
from sqlalchemy import select
from app.db.session import engine,async_session_maker
from app.models.user import User
from app.models.plan import Plan
from app.models.organization import Organization
from app.services.analysis_service import generate_insight_for_creative
from app.services.ai.ai_router import AIRouter
from app.services.ai.base import AIProvider
class Failed(AIProvider):
 async def _call_api(self,messages):raise RuntimeError('synthetic provider outage')
async def fake(*a,**k):return Failed()
async def main():
 AIRouter.get_provider_for_user=staticmethod(fake)
 async with async_session_maker() as d:
  p=await d.get(Plan,'plan_trial_default');p.feature_flags={'intelligence':True,'swipe_files':True};await d.commit()
 async with async_session_maker() as d:
  u=await d.get(User,'bob');o=await d.get(Organization,'ob');before=o.credit_balance
  x=await generate_insight_for_creative(d,'private-creative',u)
  await d.refresh(o)
  print('provider_outage_result',x.confidence,'charged',before-o.credit_balance,'foreign_text', 'Alice private strategy' in x.summary)
 await engine.dispose()
asyncio.run(main())
