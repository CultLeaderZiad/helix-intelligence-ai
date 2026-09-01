import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath("backend"))

from dotenv import load_dotenv
load_dotenv(".env.local")
load_dotenv("backend/.env")

from app.db.session import async_session_maker
from app.models.plan import Plan
from sqlalchemy import select

async def normalize_plans():
    async with async_session_maker() as db:
        trial = (await db.execute(select(Plan).where(Plan.id == "plan_trial_default"))).scalar_one_or_none()
        if trial:
            trial.name = "7-Day Free Trial"
            trial.type = "trial"
            trial.price_monthly = 0.0
            trial.credit_allowance = 30
            trial.daily_credit_limit = 3.5
            trial.daily_image_limit = 5
            trial.daily_video_limit = 3
            trial.price_per_credit = 0.0

        payg = (await db.execute(select(Plan).where(Plan.id == "plan_payg_default"))).scalar_one_or_none()
        if payg:
            payg.name = "Pay As You Go"
            payg.type = "pay_as_you_go"
            payg.price_monthly = 29.0
            payg.credit_allowance = 100
            payg.price_per_credit = 0.01
            payg.daily_image_limit = 20
            payg.daily_video_limit = 10

        pro = (await db.execute(select(Plan).where(Plan.id == "plan_pro_9a14f8"))).scalar_one_or_none()
        if pro:
            pro.name = "Pro Growth Plan"
            pro.type = "custom"
            pro.price_monthly = 99.0
            pro.credit_allowance = 500
            pro.price_per_credit = 0.008
            pro.daily_image_limit = 50
            pro.daily_video_limit = 25

        enterprise = (await db.execute(select(Plan).where(Plan.id == "plan_enterprise_custom"))).scalar_one_or_none()
        if enterprise:
            enterprise.name = "Enterprise Custom"
            enterprise.type = "custom"
            enterprise.price_monthly = 499.0
            enterprise.credit_allowance = 5000
            enterprise.price_per_credit = 0.005
            enterprise.daily_image_limit = 200
            enterprise.daily_video_limit = 100

        await db.commit()
        print("Sanity-checked and normalized all plans in Neon DB.")

        plans = (await db.execute(select(Plan))).scalars().all()
        for p in plans:
            print(f"[{p.id}] {p.name} ({p.type}) => ${p.price_monthly}/mo, {p.credit_allowance} credits, ${p.price_per_credit}/credit, {p.daily_image_limit} img/day, {p.daily_video_limit} vid/day")

if __name__ == "__main__":
    asyncio.run(normalize_plans())
