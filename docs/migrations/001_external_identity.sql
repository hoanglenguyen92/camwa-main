-- Postgres. init_db uses create_all, which never alters existing tables, so apply this by hand.

-- Step 1: add the new columns (the app can stay online).
ALTER TABLE iam ADD COLUMN auth_uid VARCHAR(128) NULL;
ALTER TABLE iam ADD COLUMN phone_number VARCHAR(20) NULL;
CREATE UNIQUE INDEX ix_iam_auth_uid ON iam (auth_uid);
ALTER TABLE iam ADD CONSTRAINT iam_phone_number_key UNIQUE (phone_number);
ALTER TABLE iam ALTER COLUMN password DROP NOT NULL;

-- Backfill from the repo root, then continue:
--   python -m scripts.link_identities
-- The script reports rows it could not link. Fix those before step 2.

-- Step 2: enforce the new schema and drop the local credential columns.
ALTER TABLE iam ALTER COLUMN auth_uid SET NOT NULL;
ALTER TABLE iam DROP COLUMN password;
ALTER TABLE iam DROP COLUMN failed_attempts;
ALTER TABLE iam DROP COLUMN locked_until;
ALTER TABLE iam DROP COLUMN last_attempt_at;
