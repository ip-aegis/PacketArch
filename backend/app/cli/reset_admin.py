# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Reset or create a local admin password — recovery without DB surgery.

Run inside the backend container (the scripts/reset-admin.sh wrapper does this):
    python -m app.cli.reset_admin --username admin

If the user exists it resets the password and ensures admin + active; if not,
it creates a local admin. LDAP-backed users are refused (their password lives
in the directory). The action is written to the user audit log (actor "cli").
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys

from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.security import get_password_hash
from app.models.user import User
from app.services.user_audit import record_user_audit


async def _run(username: str, password: str) -> int:
    async with async_session_maker() as db:
        user = (
            await db.execute(select(User).where(User.username == username))
        ).scalar_one_or_none()

        if user is None:
            user = User(
                username=username,
                password_hash=get_password_hash(password),
                is_admin=True,
                is_active=True,
                auth_source="local",
            )
            db.add(user)
            action, detail, verb = "create", "created admin via CLI", "Created"
        else:
            if user.auth_source != "local":
                print(
                    f"ERROR: '{username}' authenticates via LDAP — its password is "
                    "managed by the directory and can't be reset here.",
                    file=sys.stderr,
                )
                return 2
            user.password_hash = get_password_hash(password)
            bits = ["password reset"]
            if not user.is_admin:
                bits.append("promoted to admin")
            if not user.is_active:
                bits.append("reactivated")
            user.is_admin = True
            user.is_active = True
            action, detail, verb = "reset_password", ", ".join(bits) + " via CLI", "Updated"

        await db.flush()
        record_user_audit(db, actor="cli", action=action, target=user, detail=detail)
        await db.commit()
        print(f"{verb} admin user '{username}' (admin=True, active=True).")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reset or create a local PacketArch admin password."
    )
    parser.add_argument("--username", default="admin", help='Username (default: "admin")')
    parser.add_argument(
        "--password",
        help="New password. Omit to be prompted securely (recommended — keeps it "
        "out of shell history and the process list).",
    )
    args = parser.parse_args()

    password = args.password
    if not password:
        password = getpass.getpass("New password: ")
        if password != getpass.getpass("Confirm password: "):
            print("ERROR: passwords do not match.", file=sys.stderr)
            sys.exit(1)
    if len(password) < 8:
        print("ERROR: password must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)

    sys.exit(asyncio.run(_run(args.username, password)))


if __name__ == "__main__":
    main()
