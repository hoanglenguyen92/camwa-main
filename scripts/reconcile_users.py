"""Lists app profiles with no Keycloak account and Keycloak accounts with no app profile.

    python -m scripts.reconcile_users
Exits 1 when either list is non-empty.
"""
import asyncio
import sys

from sqlalchemy import select

from backend.core.db import AsyncSessionLocal
from backend.core.keycloak import keycloak
from backend.models import AcademicCoordinator, FacilityFaculty, Lecturer, Student

PROFILES = (
    ("STUDENT", Student.student_id),
    ("LECTURER", Lecturer.lecturer_id),
    ("AC", AcademicCoordinator.ac_id),
    ("FA", FacilityFaculty.staff_id),
)


async def reconcile() -> int:
    accounts = {a.camwa_id: a for a in await keycloak.list_users()}
    profile_ids: set[str] = set()
    missing_accounts: list[str] = []
    async with AsyncSessionLocal() as session:
        for role, column in PROFILES:
            for camwa_id in await session.scalars(select(column)):
                profile_ids.add(camwa_id)
                if camwa_id not in accounts:
                    missing_accounts.append(f"{role} {camwa_id}")
    service_accounts = {u for u in accounts if u.startswith("service-account-")}
    missing_profiles = sorted(set(accounts) - profile_ids - service_accounts)

    print(f"Profiles with no account ({len(missing_accounts)}):")
    for line in missing_accounts:
        print(f"  {line}")
    print(f"Accounts with no profile ({len(missing_profiles)}), ADMIN accounts are expected here:")
    for camwa_id in missing_profiles:
        print(f"  {camwa_id}{'' if accounts[camwa_id].active else ' (inactive)'}")
    return 1 if missing_accounts or missing_profiles else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(reconcile()))
