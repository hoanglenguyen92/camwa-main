"""Link iam rows to the configured identity provider (AUTH_PROVIDER).

Default: link rows whose auth_uid IS NULL. Run after step 1 of docs/migrations/001_external_identity.sql.
--relink: relink EVERY row to the current provider. This is the provider-switch tool.
Each row is linked to the provider user with the same email, or a user is created without a password.
Safe to rerun.

Usage: python -m scripts.link_identities [--relink]
"""
import argparse
import asyncio

from sqlalchemy import text

from backend.core.db import AsyncSessionLocal, engine
from backend.core.identity import provider as identity


async def link(relink: bool) -> None:
    linked = created = failed = 0
    query = "SELECT iam_id, email FROM iam" + ("" if relink else " WHERE auth_uid IS NULL")
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(text(query))).all()
        for iam_id, email in rows:
            try:
                uid = await identity.get_uid_by_email(email)
                if uid:
                    linked += 1
                else:
                    uid = await identity.create_user(email)
                    created += 1
                await session.execute(
                    text("UPDATE iam SET auth_uid = :uid WHERE iam_id = :iam_id"),
                    {"uid": uid, "iam_id": iam_id},
                )
                await session.commit()
            except Exception as e:
                await session.rollback()
                failed += 1
                print(f"FAILED {iam_id} <{email}>: {getattr(e, 'detail', e)}")
    await engine.dispose()
    print(f"Done: {linked} linked to existing provider users, {created} created, {failed} failed, {len(rows)} total.")
    print("Created users have no password. They set one with POST /api/auth/forgot-password unless password hashes were imported into the provider.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--relink", action="store_true", help="relink every row, not just rows with no auth_uid")
    asyncio.run(link(parser.parse_args().relink))
