-- Run this ONLY if you already ran the old schema.sql (adds the friend system).
-- New setups can skip it: schema.sql now includes the table.
CREATE TABLE IF NOT EXISTS friend_requests (
  sender_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  recipient_id  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status        TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted')),
  sender_seen   BOOLEAN NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  responded_at  TIMESTAMPTZ,
  PRIMARY KEY (sender_id, recipient_id),
  CHECK (sender_id <> recipient_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS friend_requests_pair
  ON friend_requests (LEAST(sender_id, recipient_id), GREATEST(sender_id, recipient_id));
CREATE INDEX IF NOT EXISTS friend_requests_recipient ON friend_requests (recipient_id);
