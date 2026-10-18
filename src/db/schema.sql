-- Work Along With Me: database schema for Tiger Data (Postgres)
-- Run this once in the Tiger Data console's SQL editor.

CREATE TABLE IF NOT EXISTS users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  display_name  TEXT NOT NULL,
  hero_name     TEXT,
  avatar        TEXT,
  is_demo       BOOLEAN NOT NULL DEFAULT FALSE,
  auth0_sub     TEXT UNIQUE,   -- Auth0 user ID; NULL for demo users
  -- /aboutyou form: users can't reach /home until about_you_completed is TRUE
  organization         TEXT,
  track                TEXT CHECK (track IN ('gators', 'turtle')),
  about_you_completed  BOOLEAN NOT NULL DEFAULT FALSE,
  -- /quiz comes right after /aboutyou; /home stays locked until it's TRUE too
  quiz_completed       BOOLEAN NOT NULL DEFAULT FALSE,
  -- Uploaded file in uploads/profile_pictures/ (Flask); NULL = default assets/donkey.jpg.
  -- Separate from avatar, which is the quest hero's animal (e.g. 'fox').
  profile_picture      TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per student. Each quest fills in its own columns.
--
-- Gumdrop Citadel (how you handle work):
--   task_format:   'list' | 'cards' | 'checklist'
--   task_size:     'large' | 'bite_sized'
--   pacing:        'single_deadline' | 'checkins' | 'flexible'
--   info_styles:   any of 'written','visual','verbal','demonstration'
--   roles:         any of 'leader','builder','researcher','designer','presenter'
--
-- Sourpuss Keep (how you communicate):
--   communication:     'text' | 'voice' | 'in_person' | 'mix'
--   processing_time:   'instant' | 'take_time'
--   feedback_style:    'direct' | 'gentle' | 'written' | 'private'
--   cool_down:         'break_signal' | 'step_away' | 'switch_to_text' | 'none'
--   presentation_role: 'lead' | 'short_part' | 'behind_scenes'
--
-- visibility: per-field privacy, e.g. {"cool_down": "private", "pacing": "public"}
--   'public'      = shown on hero card + used for matching
--   'after_match' = used for matching, only shown once a group forms
--   'private'     = never used or shown
CREATE TABLE IF NOT EXISTS profiles (
  user_id            UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  task_format        TEXT,
  task_size          TEXT,
  pacing             TEXT,
  info_styles        TEXT[] NOT NULL DEFAULT '{}',
  roles              TEXT[] NOT NULL DEFAULT '{}',
  communication      TEXT,
  processing_time    TEXT,
  feedback_style     TEXT,
  cool_down          TEXT,
  presentation_role  TEXT,
  visibility         JSONB NOT NULL DEFAULT '{}'::jsonb,
  completed_quests   TEXT[] NOT NULL DEFAULT '{}',   -- badges, e.g. {kanban_canyon}
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Friend system (/connections). One row per pair of users:
--   'pending'  = sender asked, recipient hasn't answered
--   'accepted' = they're friends
-- Rejecting deletes the row, so the sender sees no "request pending" and can ask again.
-- sender_seen: FALSE once accepted, until the sender opens their Friends tab (drives its highlight).
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
-- At most one row per pair, whichever direction it was sent in
CREATE UNIQUE INDEX IF NOT EXISTS friend_requests_pair
  ON friend_requests (LEAST(sender_id, recipient_id), GREATEST(sender_id, recipient_id));
CREATE INDEX IF NOT EXISTS friend_requests_recipient ON friend_requests (recipient_id);

-- blocker_id blocked blocked_id. Blocking deletes any friendship/request between them;
-- the blocked user can't find the blocker in search or send them requests.
CREATE TABLE IF NOT EXISTS blocks (
  blocker_id  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  blocked_id  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (blocker_id, blocked_id),
  CHECK (blocker_id <> blocked_id)
);
CREATE INDEX IF NOT EXISTS blocks_blocked ON blocks (blocked_id);

-- Projects created on /project_create. owner_id is the publishing user;
-- teammates they invited are in project_contributors.
CREATE TABLE IF NOT EXISTS projects (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title        TEXT NOT NULL CHECK (btrim(title) <> ''),
  summary      TEXT NOT NULL CHECK (btrim(summary) <> ''),
  description  TEXT,
  thumbnail    TEXT,   -- uploaded file in uploads/project_thumbnails/ (Flask); NULL = none
  -- When the owner put it on the board (people can ask to collaborate); NULL = not on the board
  board_added_at  TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS projects_owner ON projects (owner_id);
CREATE INDEX IF NOT EXISTS projects_on_board ON projects (board_added_at DESC) WHERE board_added_at IS NOT NULL;

-- Teammates are invited: 'pending' until they accept on /invites. Rejecting deletes the row.
CREATE TABLE IF NOT EXISTS project_contributors (
  project_id  UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status      TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted')),
  invited_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, user_id)
);
CREATE INDEX IF NOT EXISTS project_contributors_user ON project_contributors (user_id);

-- Requests to become a collaborator on a project that's on the board (sent from /project/<id>)
CREATE TABLE IF NOT EXISTS collaborator_requests (
  project_id    UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  requested_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, user_id)
);
CREATE INDEX IF NOT EXISTS collaborator_requests_user ON collaborator_requests (user_id);

-- Posts from /create_post: up to 250 characters of text and/or one image, shown on /home.
CREATE TABLE IF NOT EXISTS posts (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  author_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  body        TEXT CONSTRAINT posts_body_length CHECK (char_length(body) <= 250),
  image       TEXT,   -- uploaded file in uploads/post_images/ (Flask); NULL = none
  -- Optional linked project the author created or joined; cleared if the project is deleted
  project_id  UUID REFERENCES projects(id) ON DELETE SET NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (btrim(coalesce(body, '')) <> '' OR image IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS posts_author_created ON posts (author_id, created_at DESC);

-- Groups formed in the Party Camp, plus the Gemini-written team guide.
CREATE TABLE IF NOT EXISTS groups (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,
  team_guide  TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS group_members (
  group_id  UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
  user_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (group_id, user_id)
);
