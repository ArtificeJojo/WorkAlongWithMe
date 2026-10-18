-- Run this ONLY if you already ran the old schema.sql (technical skills on /aboutyou).
-- New setups can skip it: schema.sql now includes the column.
-- Users need at least one skill before they can reach /home, so existing users are sent back to /aboutyou once.
ALTER TABLE users ADD COLUMN IF NOT EXISTS skills TEXT[] NOT NULL DEFAULT '{}';
