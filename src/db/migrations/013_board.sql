-- Run this ONLY if you already ran the old schema.sql (lets owners put projects on the board).
-- New setups can skip it: schema.sql now includes these.
ALTER TABLE projects ADD COLUMN IF NOT EXISTS board_added_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS projects_on_board ON projects (board_added_at DESC) WHERE board_added_at IS NOT NULL;
