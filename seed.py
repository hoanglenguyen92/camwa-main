import asyncio
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import select
from backend.core.db import AsyncSessionLocal
from backend.core.identity import provider as identity
from backend.models import Iam, Intake, Program, Semester

load_dotenv()


async def seed():
    async with AsyncSessionLocal() as session:

        # Program
        program_id = "CSE"
        existing_program = await session.get(Program, program_id)
        if not existing_program:
            session.add(Program(program_id=program_id, name="Computer Science"))

        # Intake
        intake_year = 2021
        existing_intake = await session.get(Intake, intake_year)
        if not existing_intake:
            session.add(Intake(year=intake_year))

        # Semester
        sem_id = "WS2025"
        existing_sem = await session.get(Semester, sem_id)
        if not existing_sem:
            session.add(
                Semester(
                    sem_id=sem_id,
                    start_date=datetime(2025, 9, 1),
                    end_date=datetime(2026, 2, 28),
                )
            )
        # Admin account in IAM
        admin_id = "admin"
        existing_admin = await session.get(Iam, admin_id)
        if not existing_admin:
            admin_email = "admin@example.com"
            admin_uid = await identity.get_uid_by_email(admin_email)
            if admin_uid is None:
                admin_password = os.environ.get("SEED_ADMIN_PASSWORD")
                if not admin_password:
                    sys.exit("SEED_ADMIN_PASSWORD is not set. Set it in the environment to create the admin account.")
                admin_uid = await identity.create_user(admin_email, admin_password)
            session.add(
                Iam(
                    iam_id=admin_id,
                    username="admin",
                    email=admin_email,
                    firebase_uid=admin_uid,
                    role="ADMIN",
                    token_version=1,
                )
            )
        await session.commit()
        print("Seed completed.")
if __name__ == "__main__":
    asyncio.run(seed())