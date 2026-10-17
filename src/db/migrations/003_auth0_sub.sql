-- Run this ONLY if you already ran the old schema.sql (links users to Auth0 accounts).
-- New setups can skip it: schema.sql now includes the column.
ALTER TABLE users ADD COLUMN IF NOT EXISTS auth0_sub TEXT UNIQUE;
