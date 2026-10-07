import os,sys,asyncio,httpx
sys.path.insert(0,os.getcwd())
from app.main import app
from app.db.session import engine
async def main():
 async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,raise_app_exceptions=False),base_url='http://local') as c:
  h=await c.get('/api/health');print('health',h.status_code,h.text)
  s=await c.post('/api/auth/sign-in',json={'email':'synthetic@example.com','password':'Synthetic123!'}); print('signin',s.status_code)
 await engine.dispose()
asyncio.run(main())
