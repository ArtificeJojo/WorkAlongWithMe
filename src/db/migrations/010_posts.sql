-- Run this ONLY if you already ran the old schema.sql (adds posts).
-- New setups can skip it: schema.sql now includes the table.
CREATE TABLE IF NOT EXISTS posts (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  author_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  body        TEXT,
  image       TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (btrim(coalesce(body, '')) <> '' OR image IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS posts_author_created ON posts (author_id, created_at DESC);
