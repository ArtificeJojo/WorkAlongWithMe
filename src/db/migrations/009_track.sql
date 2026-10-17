-- Run this ONLY if you already ran the old schema.sql (adds the /aboutyou track).
-- New setups can skip it: schema.sql now includes the column.
ALTER TABLE users ADD COLUMN IF NOT EXISTS track TEXT CHECK (track IN ('gators', 'turtle'));

-- Everyone answers /aboutyou again to pick a track (their other answers are pre-filled)
UPDATE users SET about_you_completed = FALSE;
