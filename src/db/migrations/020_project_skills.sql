-- Run this ONLY if you already ran the old schema.sql (up to 5 skills on each project).
-- New setups can skip it: schema.sql now includes the column.
ALTER TABLE projects ADD COLUMN IF NOT EXISTS skills TEXT[] NOT NULL DEFAULT '{}';
