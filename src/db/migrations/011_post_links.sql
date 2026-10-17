-- Run this ONLY if you already ran the old schema.sql (posts: 250-character limit, linked projects).
-- New setups can skip it: schema.sql now includes these.
ALTER TABLE posts ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE SET NULL;

-- Posts are now limited to 250 characters instead of 150 words. Existing longer posts are kept
-- as they are (NOT VALID only checks new and edited rows).
ALTER TABLE posts DROP CONSTRAINT IF EXISTS posts_body_length;
ALTER TABLE posts ADD CONSTRAINT posts_body_length CHECK (char_length(body) <= 250) NOT VALID;
