// Quest definitions and answer checking. No database needed.
import { describe, expect, it } from "vitest";
import { ALLOWED, CHOOSE_POWERS, KANBAN_SWAMP, QUESTS, checkAnswer, summarize } from "@/lib/quests";
import { PROFILE_FIELDS } from "@/lib/matching";

describe("Kanban Swamp definition", () => {
  it("only offers choices the database accepts", () => {
    for (const scene of [...KANBAN_SWAMP.scenes, CHOOSE_POWERS]) {
      for (const choice of scene.choices) {
        expect(ALLOWED[scene.field], `${scene.id} → ${choice.value}`).toContain(choice.value);
      }
    }
  });

  it("has the four locked scenes, in order", () => {
    expect(KANBAN_SWAMP.scenes.map((s) => [s.id, s.field])).toEqual([
      ["workbench", "task_format"],
      ["mega_bug", "task_size"],
      ["launch_bridge", "pacing"],
      ["locked_gate", "info_styles"],
    ]);
  });

  it("is guided by Chomp and awards the Swamp Launcher badge", () => {
    expect(KANBAN_SWAMP.id).toBe("kanban_swamp");
    expect(KANBAN_SWAMP.badge).toBe("Swamp Launcher");
    for (const s of KANBAN_SWAMP.scenes) expect(s.speaker).toBe("Chomp");
  });

  it("offers every allowed value somewhere in its scene (no dead database options)", () => {
    for (const scene of [...KANBAN_SWAMP.scenes, CHOOSE_POWERS]) {
      expect(scene.choices.map((c) => c.value).sort()).toEqual([...ALLOWED[scene.field]].sort());
    }
  });

  it("gives every choice an emoji, label and reaction, with unique values", () => {
    for (const scene of [...KANBAN_SWAMP.scenes, CHOOSE_POWERS]) {
      const values = scene.choices.map((c) => c.value);
      expect(new Set(values).size).toBe(values.length);
      for (const c of scene.choices) {
        expect(c.emoji).toBeTruthy();
        expect(c.label).toBeTruthy();
        expect(c.reaction).toBeTruthy();
      }
    }
  });

  it("has no losing outcomes: every MEGA-BUG choice is a win", () => {
    const megaBug = KANBAN_SWAMP.scenes.find((s) => s.id === "mega_bug")!;
    for (const c of megaBug.choices) expect(c.reaction).not.toMatch(/lose|lost|fail|game over/i);
  });

  it("lets the locked gate pick one hint, and powers pick up to two", () => {
    expect(KANBAN_SWAMP.scenes.find((s) => s.id === "locked_gate")!.multi).toBe(1);
    expect(CHOOSE_POWERS.multi).toBe(2);
  });

  it("is registered in QUESTS", () => {
    expect(QUESTS).toEqual({ kanban_swamp: KANBAN_SWAMP });
  });

  it("has an allowed-values list for every profile field", () => {
    for (const f of PROFILE_FIELDS) expect(ALLOWED[f].length).toBeGreaterThan(0);
  });
});

describe("checkAnswer", () => {
  it("accepts real choices", () => {
    expect(checkAnswer("task_size", "bite_sized")).toBeNull();
    expect(checkAnswer("info_styles", ["visual"])).toBeNull();
    expect(checkAnswer("roles", ["builder", "designer"])).toBeNull();
    expect(checkAnswer("roles", [])).toBeNull();
  });

  it("accepts a skipped single-choice scene", () => {
    expect(checkAnswer("pacing", null)).toBeNull();
  });

  it("rejects made-up choices", () => {
    expect(checkAnswer("task_size", "medium")).not.toBeNull();
    expect(checkAnswer("roles", ["wizard"])).not.toBeNull();
  });

  it("rejects the wrong shape", () => {
    expect(checkAnswer("roles", "builder")).not.toBeNull();
    expect(checkAnswer("task_size", ["bite_sized"])).not.toBeNull();
    expect(checkAnswer("task_size", 5)).not.toBeNull();
  });

  it("limits list answers to 2 and rejects duplicates", () => {
    expect(checkAnswer("roles", ["builder", "designer", "leader"])).toMatch(/at most 2/);
    expect(checkAnswer("info_styles", ["visual", "visual"])).toMatch(/duplicate/);
  });
});

describe("summarize", () => {
  it("turns answers into friendly lines, in scene order", () => {
    const lines = summarize(KANBAN_SWAMP, {
      info_styles: ["visual"],
      task_format: "cards",
      task_size: "bite_sized",
    });
    expect(lines).toEqual([
      "🧩 Sticky-note blocks I can move around",
      "✂️ Slice it into tiny bugs",
      "🖼️ A diagram",
    ]);
  });

  it("skips scenes with no answer", () => {
    expect(summarize(KANBAN_SWAMP, {})).toEqual([]);
  });
});
