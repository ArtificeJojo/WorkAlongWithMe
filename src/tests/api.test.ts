// End-to-end tests: real API routes against your real database.
// Needs DATABASE_URL in .env.local and schema.sql + seed.sql already run.
// Every hero these tests create is named "__test__" and deleted afterwards.
import { afterAll, beforeAll, describe, expect, it } from "vitest";

const hasDb = !!process.env.DATABASE_URL;

describe.skipIf(!hasDb)("API + database", async () => {
  const profile = await import("@/app/api/profile/route");
  const matches = await import("@/app/api/matches/route");
  const health = await import("@/app/api/health/route");
  const { pool } = await import("@/lib/db");

  const TEST_NAME = "__test__";
  const j = async (r: Response) => ({ status: r.status, body: await r.json() });
  const save = (body: unknown) =>
    profile
      .POST(new Request("http://test/api/profile", { method: "POST", body: JSON.stringify(body) }))
      .then(j);
  const getMatches = (userId: string, n?: number) =>
    matches
      .GET(new Request(`http://test/api/matches?userId=${userId}${n ? `&n=${n}` : ""}`))
      .then(j);

  const swampAnswers = {
    task_format: "cards",
    task_size: "bite_sized",
    pacing: "checkins",
    info_styles: ["visual"],
    roles: ["builder"],
  };

  const cleanup = () => pool.query("DELETE FROM users WHERE display_name = $1", [TEST_NAME]);
  beforeAll(cleanup);
  afterAll(async () => {
    await cleanup();
    await pool.end();
  });

  it("health check connects and sees the demo heroes", async () => {
    const { status, body } = await j(await health.GET());
    expect(status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.heroes).toBeGreaterThanOrEqual(12);
  });

  it("finishing Kanban Swamp creates a hero with answers and a badge", async () => {
    const { status, body } = await save({
      displayName: TEST_NAME,
      heroName: "Test the Brave",
      avatar: "raccoon",
      answers: swampAnswers,
      completedQuest: "kanban_swamp",
    });
    expect(status).toBe(200);
    expect(body.profile).toMatchObject({ ...swampAnswers, hero_name: "Test the Brave" });
    expect(body.profile.completed_quests).toEqual(["kanban_swamp"]);
  });

  it("replaying a quest doesn't duplicate the badge", async () => {
    const first = await save({ displayName: TEST_NAME, answers: swampAnswers, completedQuest: "kanban_swamp" });
    const id = first.body.profile.user_id;
    const again = await save({ userId: id, answers: swampAnswers, completedQuest: "kanban_swamp" });
    expect(again.body.profile.completed_quests).toEqual(["kanban_swamp"]);
  });

  it("a second quest's save keeps the first quest's answers", async () => {
    const first = await save({ displayName: TEST_NAME, answers: swampAnswers });
    const id = first.body.profile.user_id;
    const second = await save({
      userId: id,
      answers: { communication: "text", processing_time: "take_time", presentation_role: "behind_scenes" },
    });
    expect(second.body.profile).toMatchObject({ ...swampAnswers, communication: "text" });
  });

  it("privacy choices merge instead of overwriting", async () => {
    const first = await save({ displayName: TEST_NAME, answers: {}, visibility: { cool_down: "private" } });
    const id = first.body.profile.user_id;
    const second = await save({ userId: id, visibility: { pacing: "after_match" } });
    expect(second.body.profile.visibility).toEqual({ cool_down: "private", pacing: "after_match" });
  });

  it("ignores unknown privacy values and fields", async () => {
    const r = await save({ displayName: TEST_NAME, visibility: { pacing: "everyone", hacker: "public" } });
    expect(r.status).toBe(200);
    expect(r.body.profile.visibility).toEqual({});
  });

  it("GET /api/profile returns the hero", async () => {
    const created = await save({ displayName: TEST_NAME, answers: swampAnswers });
    const id = created.body.profile.user_id;
    const got = await j(await profile.GET(new Request(`http://test/api/profile?userId=${id}`)));
    expect(got.status).toBe(200);
    expect(got.body.profile.user_id).toBe(id);
  });

  describe("rejects bad input", () => {
    it.each([
      ["a made-up choice", { displayName: TEST_NAME, answers: { task_size: "medium" } }],
      ["too many picks", { displayName: TEST_NAME, answers: { roles: ["builder", "designer", "leader"] } }],
      ["wrong shape", { displayName: TEST_NAME, answers: { roles: "builder" } }],
      ["an unknown quest", { displayName: TEST_NAME, completedQuest: "dragon_lair" }],
      ["no name for a new hero", { answers: swampAnswers }],
      ["a malformed hero id", { userId: "not-a-uuid", answers: swampAnswers }],
      ["a hero id that doesn't exist", { userId: "00000000-0000-0000-0000-999999999999", answers: swampAnswers }],
    ])("%s → 400", async (_label, body) => {
      const r = await save(body);
      expect(r.status).toBe(400);
      expect(r.body.error).toBeTruthy();
    });

    it("invalid JSON → 400", async () => {
      const r = await profile.POST(new Request("http://test/api/profile", { method: "POST", body: "{oops" }));
      expect(r.status).toBe(400);
    });

    it("a rejected save doesn't create a half-made hero", async () => {
      const before = await pool.query("SELECT count(*)::int AS n FROM users WHERE display_name = $1", [TEST_NAME]);
      await save({ displayName: TEST_NAME, answers: { task_size: "medium" } });
      const after = await pool.query("SELECT count(*)::int AS n FROM users WHERE display_name = $1", [TEST_NAME]);
      expect(after.rows[0].n).toBe(before.rows[0].n);
    });
  });

  describe("matching", () => {
    it("returns top matches from the demo heroes", async () => {
      const me = await save({
        displayName: TEST_NAME,
        answers: { ...swampAnswers, communication: "text", presentation_role: "behind_scenes" },
      });
      const r = await getMatches(me.body.profile.user_id);
      expect(r.status).toBe(200);
      expect(r.body.matches).toHaveLength(3);
      const scores = r.body.matches.map((m: any) => m.score);
      expect(scores).toEqual([...scores].sort((a, b) => b - a));
      expect(r.body.matches[0].reasons.length).toBeGreaterThan(0);
      expect(r.body.matches.map((m: any) => m.hero.user_id)).not.toContain(me.body.profile.user_id);
    });

    it("never shows another hero's private or after_match answers", async () => {
      const me = await save({ displayName: TEST_NAME, answers: { communication: "text" } });
      const r = await getMatches(me.body.profile.user_id, 10);
      for (const m of r.body.matches) {
        expect(m.hero).not.toHaveProperty("cool_down");
        expect(m.hero).not.toHaveProperty("processing_time");
        expect(m.hero).not.toHaveProperty("feedback_style");
        expect(m.hero).not.toHaveProperty("visibility");
      }
    });

    it("unknown hero → 404, missing id → 400", async () => {
      expect((await getMatches("00000000-0000-0000-0000-999999999999")).status).toBe(404);
      const r = await matches.GET(new Request("http://test/api/matches"));
      expect(r.status).toBe(400);
    });
  });
});
