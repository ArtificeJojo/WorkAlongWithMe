// "Is Kanban Swamp functional?" Plays the quest through the real API and database
// exactly like the game screens will, including every possible choice.
// Needs DATABASE_URL in .env.local. Test heroes are named "__test__" and deleted after.
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { CHOOSE_POWERS, KANBAN_SWAMP, summarize } from "@/lib/quests";

const hasDb = !!process.env.DATABASE_URL;

describe.skipIf(!hasDb)("Kanban Swamp playthrough", async () => {
  const profile = await import("@/app/api/profile/route");
  const matches = await import("@/app/api/matches/route");
  const { pool } = await import("@/lib/db");

  const TEST_NAME = "__test__";
  const save = async (body: unknown) => {
    const r = await profile.POST(
      new Request("http://test/api/profile", { method: "POST", body: JSON.stringify(body) })
    );
    return { status: r.status, body: await r.json() };
  };
  // Builds the answers object the way the game does: one entry per scene.
  const play = (pick: (sceneId: string, values: string[]) => string) => {
    const answers: Record<string, string | string[]> = {};
    for (const s of KANBAN_SWAMP.scenes) {
      const v = pick(s.id, s.choices.map((c) => c.value));
      answers[s.field] = s.multi ? [v] : v;
    }
    return answers;
  };

  const cleanup = () => pool.query("DELETE FROM users WHERE display_name = $1", [TEST_NAME]);
  beforeAll(cleanup);
  afterAll(async () => {
    await cleanup();
    await pool.end();
  });

  it("hero setup → full quest → badge, summary and matches", async () => {
    // 1. Hero setup: name, avatar, powers
    const setup = await save({
      displayName: TEST_NAME,
      heroName: "Test the Swamp Hero",
      avatar: "gator",
      answers: { [CHOOSE_POWERS.field]: ["builder", "designer"] },
    });
    expect(setup.status).toBe(200);
    const id = setup.body.profile.user_id;

    // 2. Play all four scenes, then the finale saves once
    const answers = play((sceneId) =>
      ({ workbench: "cards", mega_bug: "bite_sized", launch_bridge: "checkins", locked_gate: "visual" })[sceneId]!
    );
    const finale = await save({ userId: id, answers, completedQuest: KANBAN_SWAMP.id });
    expect(finale.status).toBe(200);

    // 3. Everything landed in Tiger Data
    expect(finale.body.profile).toMatchObject({
      task_format: "cards",
      task_size: "bite_sized",
      pacing: "checkins",
      info_styles: ["visual"],
      roles: ["builder", "designer"], // hero setup answers kept
    });
    expect(finale.body.profile.completed_quests).toEqual(["kanban_swamp"]);

    // 4. The finale card reads correctly
    expect(summarize(KANBAN_SWAMP, finale.body.profile)).toEqual([
      "🧩 Sticky-note blocks I can move around",
      "✂️ Slice it into tiny bugs",
      "🪵 One plank at a time, checking in",
      "🖼️ A diagram",
    ]);

    // 5. The hero can head to the Tavern
    const m = await matches.GET(new Request(`http://test/api/matches?userId=${id}`));
    const mb = await m.json();
    expect(m.status).toBe(200);
    expect(mb.matches.length).toBe(3);
    expect(mb.matches[0].reasons.length).toBeGreaterThan(0);
  });

  // Every choice in every scene must save. Catches typos between the story and the database.
  for (const scene of KANBAN_SWAMP.scenes) {
    for (const choice of scene.choices) {
      it(`${scene.title}: "${choice.label}" saves as ${choice.value}`, async () => {
        const answers = play((sceneId, values) => (sceneId === scene.id ? choice.value : values[0]));
        const r = await save({ displayName: TEST_NAME, answers, completedQuest: KANBAN_SWAMP.id });
        expect(r.status).toBe(200);
        const saved = r.body.profile[scene.field];
        expect(scene.multi ? saved : [saved]).toEqual([choice.value]);
      });
    }
  }

  it("skipping a scene still finishes the quest", async () => {
    const r = await save({
      displayName: TEST_NAME,
      answers: { task_format: "list", task_size: null, pacing: null, info_styles: [] },
      completedQuest: KANBAN_SWAMP.id,
    });
    expect(r.status).toBe(200);
    expect(r.body.profile.completed_quests).toEqual(["kanban_swamp"]);
  });

  it("replaying the quest updates answers without a second badge", async () => {
    const first = await save({ displayName: TEST_NAME, answers: { task_size: "large" }, completedQuest: KANBAN_SWAMP.id });
    const id = first.body.profile.user_id;
    const again = await save({ userId: id, answers: { task_size: "bite_sized" }, completedQuest: KANBAN_SWAMP.id });
    expect(again.body.profile.task_size).toBe("bite_sized");
    expect(again.body.profile.completed_quests).toEqual(["kanban_swamp"]);
  });

  it("the old Kanban Canyon quest id is no longer accepted", async () => {
    const r = await save({ displayName: TEST_NAME, completedQuest: "kanban_canyon" });
    expect(r.status).toBe(400);
  });
});
