-- Run this ONLY if you already ran the old schema.sql (adds blocking users).
-- New setups can skip it: schema.sql now includes the table.
CREATE TABLE IF NOT EXISTS blocks (
  blocker_id  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  blocked_id  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (blocker_id, blocked_id),
  CHECK (blocker_id <> blocked_id)
);
CREATE INDEX IF NOT EXISTS blocks_blocked ON blocks (blocked_id);
