-- Run this ONLY if you already ran the old schema.sql (cosmetic red "Admin" tag on profiles).
-- New setups can skip it: schema.sql now includes the column.
-- No one is an admin by default. Give the tag by user id, e.g.:
--   UPDATE users SET is_admin = TRUE WHERE id IN ('<user id>', '<user id>');
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;
