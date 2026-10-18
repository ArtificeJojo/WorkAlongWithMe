-- Run this ONLY if you already ran the old schema.sql (adds the /quiz completion flag).
-- New setups can skip it: schema.sql now includes the column.
-- Existing users start with FALSE too, so they'll be sent to /quiz on their next visit.
ALTER TABLE users ADD COLUMN IF NOT EXISTS quiz_completed BOOLEAN NOT NULL DEFAULT FALSE;
