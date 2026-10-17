-- Work Along With Me: database schema for Tiger Data (Postgres)
-- Run this once in the Tiger Data console's SQL editor.

CREATE TABLE IF NOT EXISTS users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  display_name  TEXT NOT NULL,
  hero_name     TEXT,
  avatar        TEXT,
  is_demo       BOOLEAN NOT NULL DEFAULT FALSE,
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
