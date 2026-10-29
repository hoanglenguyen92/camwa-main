"""Writes the iam table as a /api/v1/users/imports CSV, so existing accounts move to Keycloak.

Run before docs/migrations/003_keycloak_user_store.sql drops iam:
    python -m scripts.export_iam_csv > users.csv
Rows the import would reject are left out and listed on stderr.
"""
import asyncio
import csv
import re
import sys

from sqlalchemy import text

from backend.core.db import AsyncSessionLocal
from backend.services.user_service import CSV_COLUMNS

PROFILE_SQL = {
    "STUDENT": "SELECT name, program_id, intake FROM student WHERE student_id = :id",
    "LECTURER": "SELECT name, program_id, NULL AS intake FROM lecturer WHERE lecturer_id = :id",
    "AC": "SELECT name, program_id, NULL AS intake FROM academic_coordinator WHERE ac_id = :id",
    "FA": "SELECT name, program_id, NULL AS intake FROM facility_faculty WHERE staff_id = :id",
}


def _split_name(name: str, fallback: str) -> tuple[str, str]:
    parts = (name or "").split()
    if not parts:
        return fallback, fallback
    return (parts[0], " ".join(parts[1:]) or parts[0])


async def export(out) -> int:
    writer = csv.DictWriter(out, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    skipped = 0
    async with AsyncSessionLocal() as session:
        accounts = (await session.execute(text("SELECT iam_id, username, email, role, phone_number FROM iam ORDER BY iam_id"))).all()
        for iam_id, username, email, role, phone in accounts:
            if role == "ADMIN":
                print(f"{iam_id}: ADMIN, create it in the Keycloak console", file=sys.stderr)
                skipped += 1
                continue
            if not re.fullmatch(r"[0-9]{1,20}", iam_id):
                print(f"{iam_id}: not a numeric CAMWA id", file=sys.stderr)
                skipped += 1
                continue
            profile = (await session.execute(text(PROFILE_SQL[role]), {"id": iam_id})).first() if role in PROFILE_SQL else None
            if profile is None or not profile.program_id:
                print(f"{iam_id}: {role} has no profile with a program", file=sys.stderr)
                skipped += 1
                continue
            first, last = _split_name(profile.name, username)
            writer.writerow({
                "camwa_id": iam_id,
                "email": email,
                "first_name": first,
                "last_name": last,
                "role": role,
                "program_id": profile.program_id,
                "intake": profile.intake if profile.intake is not None else "",
                "phone_number": phone or "",
            })
    return skipped


if __name__ == "__main__":
    skipped = asyncio.run(export(sys.stdout))
    print(f"{skipped} row(s) left out", file=sys.stderr)
