"""Seeds reference data, and optionally demo accounts, into the app database and Keycloak.

    python seed.py                 # program CSE, intake 2021, semester WS2025
    python seed.py --demo-users    # also one FA, LECTURER, AC and STUDENT, password from SEED_DEMO_PASSWORD

Safe to rerun. Demo users are refused unless Keycloak is local.
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

from backend.core.configs import settings  # noqa: E402
from backend.core.db import AsyncSessionLocal, engine, init_db  # noqa: E402
from backend.core.keycloak import NewUser, keycloak  # noqa: E402
from backend.models import Intake, Program, Semester  # noqa: E402
from backend.models.enums import AccountRole  # noqa: E402
from backend.schemas.users import UserImportRow  # noqa: E402
from backend.services.user_service import ensure_profiles  # noqa: E402

LOCAL_KEYCLOAK_HOSTS = ("localhost", "127.0.0.1")
PROGRAM_ID = "CSE"
INTAKE_YEAR = 2021
DEMO_USERS = (
    ("90001", AccountRole.FA, "Demo", "Faculty"),
    ("90002", AccountRole.LECTURER, "Demo", "Lecturer"),
    ("90003", AccountRole.AC, "Demo", "Coordinator"),
    ("90004", AccountRole.STUDENT, "Demo", "Student"),
)


async def seed_reference_data(session) -> None:
    if not await session.get(Program, PROGRAM_ID):
        session.add(Program(program_id=PROGRAM_ID, name="Computer Science"))
    if not await session.get(Intake, INTAKE_YEAR):
        session.add(Intake(year=INTAKE_YEAR))
    if not await session.get(Semester, "WS2025"):
        session.add(Semester(sem_id="WS2025", start_date=datetime(2025, 9, 1), end_date=datetime(2026, 2, 28)))
    await session.commit()
    print(f"Reference data: program {PROGRAM_ID}, intake {INTAKE_YEAR}, semester WS2025")


async def seed_demo_users(session, password: str) -> None:
    for camwa_id, role, first_name, last_name in DEMO_USERS:
        row = UserImportRow(
            camwa_id=camwa_id,
            email=f"demo.{role.value.lower()}@example.com",
            first_name=first_name,
            last_name=last_name,
            role=role,
            program_id=PROGRAM_ID,
            intake=INTAKE_YEAR if role == AccountRole.STUDENT else None,
        )
        if await keycloak.get_user(camwa_id) is None:
            account = await keycloak.create_user(NewUser(camwa_id, row.email, first_name, last_name, role.value))
            await keycloak.set_password(account.id, password)
        await ensure_profiles(session, row)
        print(f"Demo {role.value}: {camwa_id} / {row.email}")


async def seed(demo_users: bool) -> None:
    password = os.environ.get("SEED_DEMO_PASSWORD")
    if demo_users:
        if urlparse(settings.KEYCLOAK_URL).hostname not in LOCAL_KEYCLOAK_HOSTS:
            sys.exit("--demo-users runs only against a local Keycloak.")
        if not password:
            sys.exit("Set SEED_DEMO_PASSWORD to seed demo users.")
    await init_db()
    try:
        async with AsyncSessionLocal() as session:
            await seed_reference_data(session)
            if demo_users:
                await seed_demo_users(session, password)
    finally:
        await engine.dispose()
    print("Seed completed.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--demo-users", action="store_true", help="also create demo accounts in Keycloak and the app")
    args = parser.parse_args()
    asyncio.run(seed(args.demo_users))


if __name__ == "__main__":
    main()
