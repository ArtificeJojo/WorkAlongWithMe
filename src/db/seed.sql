-- Demo heroes so the Tavern isn't empty. Run after schema.sql.
-- Safe to re-run: deletes old demo users first.

DELETE FROM users WHERE is_demo = TRUE;

INSERT INTO users (id, display_name, hero_name, avatar, is_demo) VALUES
  ('00000000-0000-0000-0000-000000000001', 'Maya',    'Maya the Map-Maker',      'fox',      TRUE),
  ('00000000-0000-0000-0000-000000000002', 'Jordan',  'Jordan of the Quiet Code', 'owl',      TRUE),
  ('00000000-0000-0000-0000-000000000003', 'Priya',   'Priya Pixelweaver',        'cat',      TRUE),
  ('00000000-0000-0000-0000-000000000004', 'Marcus',  'Marcus the Bold Speaker',  'bear',     TRUE),
  ('00000000-0000-0000-0000-000000000005', 'Lena',    'Lena Bugslayer',           'frog',     TRUE),
  ('00000000-0000-0000-0000-000000000006', 'Sam',     'Sam the Steady',           'turtle',   TRUE),
  ('00000000-0000-0000-0000-000000000007', 'Diego',   'Diego Datadiver',          'otter',    TRUE),
  ('00000000-0000-0000-0000-000000000008', 'Aisha',   'Aisha Skybuilder',         'bird',     TRUE),
  ('00000000-0000-0000-0000-000000000009', 'Kenji',   'Kenji the Calm Captain',   'panda',    TRUE),
  ('00000000-0000-0000-0000-000000000010', 'Rosa',    'Rosa Rhymecaster',         'bunny',    TRUE),
  ('00000000-0000-0000-0000-000000000011', 'Theo',    'Theo Gearsmith',           'raccoon',  TRUE),
  ('00000000-0000-0000-0000-000000000012', 'Nia',     'Nia Storyteller',          'deer',     TRUE);

INSERT INTO profiles
  (user_id, task_format, task_size, pacing, info_styles, roles,
   communication, processing_time, feedback_style, cool_down, presentation_role, visibility)
VALUES
  ('00000000-0000-0000-0000-000000000001', 'cards',     'bite_sized', 'checkins',        '{visual,written}',        '{designer,leader}',     'text',      'take_time', 'gentle',  'switch_to_text', 'short_part',    '{}'),
  ('00000000-0000-0000-0000-000000000002', 'checklist', 'bite_sized', 'checkins',        '{written}',               '{builder}',             'text',      'take_time', 'written', 'step_away',      'behind_scenes', '{}'),
  ('00000000-0000-0000-0000-000000000003', 'cards',     'bite_sized', 'flexible',        '{visual,demonstration}',  '{designer}',            'mix',       'take_time', 'gentle',  'break_signal',   'behind_scenes', '{}'),
  ('00000000-0000-0000-0000-000000000004', 'list',      'large',      'single_deadline', '{verbal}',                '{presenter,leader}',    'voice',     'instant',   'direct',  'none',           'lead',          '{}'),
  ('00000000-0000-0000-0000-000000000005', 'checklist', 'large',      'single_deadline', '{written}',               '{builder,researcher}',  'text',      'instant',   'direct',  'none',           'behind_scenes', '{}'),
  ('00000000-0000-0000-0000-000000000006', 'checklist', 'bite_sized', 'checkins',        '{written,visual}',        '{researcher}',          'text',      'take_time', 'private', 'step_away',      'short_part',    '{"cool_down":"private"}'),
  ('00000000-0000-0000-0000-000000000007', 'list',      'large',      'flexible',        '{written,demonstration}', '{researcher,builder}',  'mix',       'instant',   'direct',  'none',           'short_part',    '{}'),
  ('00000000-0000-0000-0000-000000000008', 'cards',     'bite_sized', 'checkins',        '{visual}',                '{builder,designer}',    'in_person', 'instant',   'gentle',  'break_signal',   'short_part',    '{}'),
  ('00000000-0000-0000-0000-000000000009', 'checklist', 'bite_sized', 'checkins',        '{written,verbal}',        '{leader,presenter}',    'text',      'take_time', 'gentle',  'break_signal',   'lead',          '{}'),
  ('00000000-0000-0000-0000-000000000010', 'cards',     'bite_sized', 'flexible',        '{verbal,visual}',         '{presenter,designer}',  'voice',     'instant',   'gentle',  'step_away',      'lead',          '{}'),
  ('00000000-0000-0000-0000-000000000011', 'list',      'large',      'single_deadline', '{demonstration}',         '{builder}',             'in_person', 'take_time', 'direct',  'step_away',      'behind_scenes', '{}'),
  ('00000000-0000-0000-0000-000000000012', 'checklist', 'bite_sized', 'checkins',        '{written,visual}',        '{presenter,researcher}','text',      'take_time', 'written', 'switch_to_text', 'lead',          '{"feedback_style":"private"}');
