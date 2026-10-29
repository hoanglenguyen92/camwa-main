-- Postgres. Keycloak now owns accounts, so the iam table goes away. Apply by hand, after a backup.
-- Dropping iam drops the emails and phone numbers it holds. Load them into Keycloak first:
--   python -m scripts.export_iam_csv > users.csv
--   POST /api/v1/users/imports with users.csv, as a CAMWA ADMIN

-- Step 1: foreign keys. Constraint names come from 002_app_owned_student_ids.sql. To confirm:
--   SELECT constraint_name, table_name FROM information_schema.table_constraints
--   WHERE constraint_type = 'FOREIGN KEY' AND table_name IN ('student', 'image_assets');
BEGIN;
ALTER TABLE student DROP CONSTRAINT student_student_id_fkey;
ALTER TABLE image_assets DROP CONSTRAINT image_assets_iam_id_fkey;
ALTER TABLE image_assets RENAME COLUMN iam_id TO camwa_id;
CREATE INDEX ix_image_assets_camwa_id ON image_assets (camwa_id);
COMMIT;

-- Step 2: once every account is in Keycloak and scripts/reconcile_users.py shows nothing missing.
DROP TABLE iam;
