"""Seed local identities only; never creatives, provider results, or production."""
import asyncio
import datetime as dt
import json
import os
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.core.security import get_password_hash
from app.db.session import worker_session_maker
from app.models.user import User
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.access_grant import AccessRequest
from app.services.admin_service import grant_organization_access


async def main():
    url = make_url(os.environ['DATABASE_URL'])
    if url.host != '127.0.0.1' or url.port != 55434 or url.database != 'helix_w6_preview':
        raise RuntimeError('Preview seed refuses any other database')
    credentials = json.loads(Path(os.environ['HELIX_LOCAL_CREDENTIALS']).read_text())
    async with worker_session_maker() as db:
        for name in ('admin', 'member', 'pending', 'other'):
            user_id = f'w6-preview-{name}'
            user = await db.get(User, user_id)
            if user is None:
                user = User(id=user_id, email=f'w6-{name}@example.com', full_name=f'W6 {name.title()}',
                            password_hash=get_password_hash(credentials['password']), role='admin' if name == 'admin' else 'customer',
                            is_platform_admin=name == 'admin', created_at=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None))
                db.add(user)
                await db.flush()
            if user.email.endswith('@example.test'):
                user.email = f'w6-{name}@example.com'
            org_id = f'w6-preview-org-{name}'
            if await db.get(Organization, org_id) is None:
                db.add(Organization(id=org_id, name=f'W6 {name.title()} Workspace', owner_id=user_id, plan='custom'))
                await db.flush()
                db.add(OrganizationMember(id=f'w6-preview-membership-{name}', org_id=org_id, user_id=user_id, role='owner'))
        await db.commit()
        admin = await db.get(User, 'w6-preview-admin')
        from app.models.access_grant import OrganizationAccessGrant
        grant = (await db.execute(select(OrganizationAccessGrant).where(OrganizationAccessGrant.org_id == 'w6-preview-org-member'))).scalars().first()
        if grant is None:
            await grant_organization_access(db, admin, 'w6-preview-org-member', 'plan_trial_default', {'discover': True})
        if await db.get(AccessRequest, 'w6-preview-request-pending') is None:
            db.add(AccessRequest(id='w6-preview-request-pending', org_id='w6-preview-org-pending', user_id='w6-preview-pending', requested_features=['discover'], note='Synthetic W6 approval verification'))
            await db.commit()
    print('Synthetic local preview identities ready (admin/member/pending/other).')


asyncio.run(main())
