-- Run this ONLY if you already ran the old schema.sql (adds quest badges).
-- New setups can skip it: schema.sql now includes the column.
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS completed_quests TEXT[] NOT NULL DEFAULT '{}';
