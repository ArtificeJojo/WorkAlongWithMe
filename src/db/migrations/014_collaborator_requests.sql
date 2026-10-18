-- Run this ONLY if you already ran the old schema.sql (requests to collaborate on board projects).
-- New setups can skip it: schema.sql now includes the table.
CREATE TABLE IF NOT EXISTS collaborator_requests (
  project_id    UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  requested_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, user_id)
);
CREATE INDEX IF NOT EXISTS collaborator_requests_user ON collaborator_requests (user_id);
