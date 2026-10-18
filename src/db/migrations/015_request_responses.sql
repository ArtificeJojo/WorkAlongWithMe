-- Run this ONLY if you already ran the old schema.sql (owners accept/reject collaborator requests).
-- New setups can skip it: schema.sql now includes these columns.
ALTER TABLE collaborator_requests
  ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected')),
  ADD COLUMN IF NOT EXISTS seen BOOLEAN NOT NULL DEFAULT FALSE;
