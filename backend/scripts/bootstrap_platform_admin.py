"""Promote the first platform admin and grant its workspace access.

Run from backend/ with DATABASE_URL pointing at the target database (the
owner role or the API login; the script binds the platform-admin RLS scope
itself). It never prints passwords, emails or connection strings.

    python scripts/bootstrap_platform_admin.py \
        --user-id <users.id> --expect-branch <neon branch id> \
        [--features discover,swipe_files,monitors] [--org-id ...] [--plan-id ...]

Without --apply it only prints what it would do. --expect-branch must equal
the branch id the server reports (`current_setting('neon.branch_id')`);
use `local` for a non-Neon Postgres. Safe to re-run: nothing changes when the
account is already an admin and its workspace already has the features.
See DEVELOPMENT.md -> "First platform admin".
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import async_session_maker  # noqa: E402
from app.services.admin_bootstrap_service import (  # noqa: E402
    BootstrapError,
    apply_bootstrap,
    plan_bootstrap,
    verify_target,
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--user-id", required=True, help="users.id of the account to promote")
    parser.add_argument("--expect-branch", required=True, help="Neon branch id the server must report, or 'local'")
    parser.add_argument("--features", default="discover", help="comma-separated grantable features (default: discover)")
    parser.add_argument("--org-id", help="workspace id; required only if the account owns several")
    parser.add_argument("--plan-id", help="plan for the grant (default: the workspace's current plan)")
    parser.add_argument("--apply", action="store_true", help="make the changes (default is a dry run)")
    return parser.parse_args(argv)


async def run(args) -> int:
    async with async_session_maker() as db:
        try:
            branch = await verify_target(db, args.expect_branch)
            print(f"target branch: {branch}")
            plan = await plan_bootstrap(
                db,
                args.user_id,
                args.features.split(","),
                org_id=args.org_id,
                plan_id=args.plan_id,
            )
            if args.apply and (plan.promote or plan.grant):
                plan = await apply_bootstrap(db, plan)
            elif args.apply:
                plan.notes.append("nothing to change")
            else:
                plan.notes.append("dry run: re-run with --apply to make these changes")
        except BootstrapError as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 2
    print(json.dumps(plan.summary(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run(parse_args())))
