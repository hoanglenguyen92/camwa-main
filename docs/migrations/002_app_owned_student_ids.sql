-- Postgres. student.student_id and image_assets.username now reference iam.iam_id (immutable, app-owned)
-- instead of the editable iam.username. Apply by hand.

-- Step 1: precheck. Both queries must return no rows before you continue.
SELECT s.student_id AS orphan_student_id
FROM student s LEFT JOIN iam i ON i.iam_id = s.student_id
WHERE i.iam_id IS NULL;

SELECT a.image_id, a.username AS orphan_username
FROM image_assets a LEFT JOIN iam i ON i.iam_id = a.username
WHERE i.iam_id IS NULL;

-- Step 2: swap the foreign keys. Constraint names below are the SQLAlchemy/Postgres defaults. To confirm:
--   SELECT constraint_name, table_name FROM information_schema.table_constraints
--   WHERE constraint_type = 'FOREIGN KEY' AND table_name IN ('student', 'image_assets');
BEGIN;
ALTER TABLE student DROP CONSTRAINT student_student_id_fkey;
ALTER TABLE image_assets DROP CONSTRAINT image_assets_username_fkey;
ALTER TABLE image_assets RENAME COLUMN username TO iam_id;
ALTER TABLE student ADD CONSTRAINT student_student_id_fkey FOREIGN KEY (student_id) REFERENCES iam (iam_id);
ALTER TABLE image_assets ADD CONSTRAINT image_assets_iam_id_fkey FOREIGN KEY (iam_id) REFERENCES iam (iam_id);
COMMIT;
