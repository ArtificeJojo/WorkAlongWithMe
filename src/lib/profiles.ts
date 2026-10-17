import { pool } from "./db";
import type { Profile } from "./matching";

const SELECT_PROFILE = `
  SELECT u.id AS user_id, u.display_name, u.hero_name, u.avatar,
         p.task_format, p.task_size, p.pacing, p.info_styles, p.roles,
         p.communication, p.processing_time, p.feedback_style, p.cool_down,
         p.presentation_role, p.visibility, p.completed_quests
  FROM users u
  JOIN profiles p ON p.user_id = u.id
`;

export async function getProfile(userId: string): Promise<Profile | null> {
  const { rows } = await pool.query(`${SELECT_PROFILE} WHERE u.id = $1`, [userId]);
  return rows[0] ?? null;
}

export async function getAllProfiles(): Promise<Profile[]> {
  const { rows } = await pool.query(SELECT_PROFILE);
  return rows;
}
