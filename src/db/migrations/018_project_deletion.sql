-- Run this ONLY if you already ran the old schema.sql (creators can delete projects; contributors are told).
-- New setups can skip it: schema.sql now includes the table.
CREATE TABLE IF NOT EXISTS deleted_project_notices (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  project_title  TEXT NOT NULL,
  deleted_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS deleted_project_notices_user ON deleted_project_notices (user_id);
