import sys,os,asyncio
sys.path.insert(0,os.getcwd())
from workers.scrapling.worker import _claim_next_job
for n in range(3):
 try: print('claim',n,_claim_next_job())
 except Exception as e: print('claim',n,type(e).__name__,str(e).splitlines()[0])
