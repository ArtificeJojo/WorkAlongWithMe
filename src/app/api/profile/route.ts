import { NextResponse } from "next/server";
import { pool } from "@/lib/db";
import { getProfile } from "@/lib/profiles";
import { PROFILE_FIELDS, type Field, type Visibility } from "@/lib/matching";
import { QUESTS, checkAnswer } from "@/lib/quests";

const VISIBILITY_VALUES: Visibility[] = ["public", "after_match", "private"];

// POST /api/profile
// Create a new hero, or save answers from a quest (each quest can save just its own fields).
// Body: { userId?, displayName?, heroName?, avatar?, answers?: {...}, visibility?: {...}, completedQuest? }
export async function POST(req: Request) {
  let body: any;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { userId, displayName, heroName, avatar } = body ?? {};
  const answers: Record<string, unknown> = body?.answers ?? {};
  const rawVisibility: Record<string, unknown> = body?.visibility ?? {};

  if (!userId && !displayName) {
    return NextResponse.json({ error: "New heroes need a displayName" }, { status: 400 });
  }

  // Only accept known fields (column names are never taken from user input)
  // and only real quest choices (see lib/quests.ts).
  const fields = PROFILE_FIELDS.filter((f) => f in answers);
  for (const f of fields) {
    const problem = checkAnswer(f, answers[f]);
    if (problem) return NextResponse.json({ error: problem }, { status: 400 });
  }

  const completedQuest: string | null = body?.completedQuest ?? null;
  if (completedQuest !== null && !(typeof completedQuest === "string" && completedQuest in QUESTS)) {
    return NextResponse.json({ error: "Unknown quest" }, { status: 400 });
  }

  const visibility: Partial<Record<Field, Visibility>> = {};
  for (const [k, v] of Object.entries(rawVisibility)) {
    if ((PROFILE_FIELDS as readonly string[]).includes(k) && VISIBILITY_VALUES.includes(v as Visibility))
      visibility[k as Field] = v as Visibility;
  }

  const client = await pool.connect();
  try {
    await client.query("BEGIN");

    let id: string = userId;
    if (!id) {
      const r = await client.query(
        "INSERT INTO users (display_name, hero_name, avatar) VALUES ($1, $2, $3) RETURNING id",
        [displayName, heroName ?? null, avatar ?? null]
      );
      id = r.rows[0].id;
    } else if (displayName || heroName || avatar) {
      await client.query(
        `UPDATE users SET display_name = COALESCE($2, display_name),
                          hero_name    = COALESCE($3, hero_name),
                          avatar       = COALESCE($4, avatar)
         WHERE id = $1`,
        [id, displayName ?? null, heroName ?? null, avatar ?? null]
      );
    }

    const cols = ["user_id", ...fields, "visibility", "completed_quests"];
    const values = [
      id,
      ...fields.map((f) => answers[f]),
      JSON.stringify(visibility),
      completedQuest ? [completedQuest] : [],
    ];
    const placeholders = cols.map((_, i) => `$${i + 1}`);
    placeholders[placeholders.length - 2] += "::jsonb";
    placeholders[placeholders.length - 1] += "::text[]";
    const updates = [
      ...fields.map((f) => `${f} = EXCLUDED.${f}`),
      "visibility = profiles.visibility || EXCLUDED.visibility",
      // Add the new badge once, keeping earlier ones.
      `completed_quests = ARRAY(SELECT DISTINCT unnest(profiles.completed_quests || EXCLUDED.completed_quests))`,
      "updated_at = now()",
    ];

    await client.query(
      `INSERT INTO profiles (${cols.join(", ")}) VALUES (${placeholders.join(", ")})
       ON CONFLICT (user_id) DO UPDATE SET ${updates.join(", ")}`,
      values
    );

    await client.query("COMMIT");
    const profile = await getProfile(id);
    return NextResponse.json({ profile });
  } catch (err: any) {
    await client.query("ROLLBACK");
    console.error("Saving profile failed:", err);
    const status = err?.code === "22P02" || err?.code === "23503" ? 400 : 500;
    return NextResponse.json({ error: "Could not save profile" }, { status });
  } finally {
    client.release();
  }
}

// GET /api/profile?userId=...
// Returns the student's own full profile (for their hero card).
// Note: no real login yet; fine for the demo, add auth before real use.
export async function GET(req: Request) {
  const userId = new URL(req.url).searchParams.get("userId");
  if (!userId) return NextResponse.json({ error: "userId is required" }, { status: 400 });
  try {
    const profile = await getProfile(userId);
    if (!profile) return NextResponse.json({ error: "Hero not found" }, { status: 404 });
    return NextResponse.json({ profile });
  } catch (err) {
    console.error("Loading profile failed:", err);
    return NextResponse.json({ error: "Could not load profile" }, { status: 500 });
  }
}
