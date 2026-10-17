-- Run this ONLY if you already ran the old schema.sql (adds the /aboutyou form fields).
-- New setups can skip it: schema.sql now includes the columns.
ALTER TABLE users ADD COLUMN IF NOT EXISTS organization TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS about_you_completed BOOLEAN NOT NULL DEFAULT FALSE;
