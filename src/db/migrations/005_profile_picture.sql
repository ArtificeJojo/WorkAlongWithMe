-- Run this ONLY if you already ran the old schema.sql (adds uploaded profile pictures).
-- New setups can skip it: schema.sql now includes the column.
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_picture TEXT;
