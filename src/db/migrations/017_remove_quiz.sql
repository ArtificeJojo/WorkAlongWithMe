-- Removes the setup quiz (/quiz) and its completion flag: after /aboutyou, users go straight to /home.
-- Safe to run whether or not 012_quiz.sql was ever run.
ALTER TABLE users DROP COLUMN IF EXISTS quiz_completed;
