"""Backfill iam.firebase_uid for existing rows. Run after step 1 of docs/migrations/001_firebase_auth.sql.

Usage: python -m scripts.migrate_iam_to_firebase
"""
import asyncio

from sqlalchemy import text

from backend.core import firebase
from backend.core.db import AsyncSessionLocal, engine


async def migrate() -> None:
    linked = created = failed = 0
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(text("SELECT iam_id, email FROM iam WHERE firebase_uid IS NULL"))).all()
        for iam_id, email in rows:
            try:
                uid = await firebase.get_uid_by_email(email)
                if uid:
                    linked += 1
                else:
                    uid = await firebase.create_user(email)
                    created += 1
                await session.execute(
                    text("UPDATE iam SET firebase_uid = :uid WHERE iam_id = :iam_id"),
                    {"uid": uid, "iam_id": iam_id},
                )
                await session.commit()
            except Exception as e:
                await session.rollback()
                failed += 1
                print(f"FAILED {iam_id} <{email}>: {getattr(e, 'detail', e)}")
    await engine.dispose()
    print(f"Backfill done: {linked} linked to existing Firebase users, {created} created, {failed} failed, {len(rows)} total.")
    print("Argon2 hashes cannot be imported into Firebase. Created users have no password, so they must use forgot-password (POST /api/auth/forgot-password) to set one.")


if __name__ == "__main__":
    asyncio.run(migrate())
