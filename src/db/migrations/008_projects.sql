-- Run this ONLY if you already ran the old schema.sql (adds projects).
-- New setups can skip it: schema.sql now includes the tables.
CREATE TABLE IF NOT EXISTS projects (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title        TEXT NOT NULL CHECK (btrim(title) <> ''),
  summary      TEXT NOT NULL CHECK (btrim(summary) <> ''),
  description  TEXT,
  thumbnail    TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS projects_owner ON projects (owner_id);

-- Teammates are invited: 'pending' until they accept on /invites. Rejecting deletes the row.
CREATE TABLE IF NOT EXISTS project_contributors (
  project_id  UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status      TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted')),
  invited_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, user_id)
);
CREATE INDEX IF NOT EXISTS project_contributors_user ON project_contributors (user_id);
