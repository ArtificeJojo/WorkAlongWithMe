// Matching rules. No database needed.
import { describe, expect, it } from "vitest";
import { scorePair, toPublicProfile, topMatches } from "@/lib/matching";
import { makeProfile } from "./helpers";

describe("scorePair", () => {
  it("rewards matching communication styles", () => {
    const a = makeProfile({ communication: "text" });
    const b = makeProfile({ communication: "text" });
    const r = scorePair(a, b);
    expect(r.score).toBe(3);
    expect(r.reasons).toContain("You both prefer text-first communication");
  });

  it("penalizes text vs voice, with no reason given", () => {
    const r = scorePair(makeProfile({ communication: "text" }), makeProfile({ communication: "voice" }));
    expect(r.score).toBe(-2);
    expect(r.reasons).toEqual([]);
  });

  it("treats 'mix' as flexible", () => {
    const r = scorePair(makeProfile({ communication: "mix" }), makeProfile({ communication: "voice" }));
    expect(r.score).toBe(1);
  });

  it("is symmetric for everything except roles", () => {
    const a = makeProfile({ communication: "text", pacing: "checkins", presentation_role: "lead" });
    const b = makeProfile({ communication: "text", pacing: "checkins", presentation_role: "behind_scenes" });
    expect(scorePair(a, b).score).toBe(scorePair(b, a).score);
  });

  it("rewards complementary roles, capped at +4", () => {
    const me = makeProfile({ roles: ["builder"] });
    expect(scorePair(me, makeProfile({ roles: ["designer"] })).score).toBe(2);
    expect(scorePair(me, makeProfile({ roles: ["designer", "presenter"] })).score).toBe(4);
    expect(scorePair(me, makeProfile({ roles: ["builder"] })).score).toBe(0);
  });

  it("loves a presenter + behind-the-scenes pair", () => {
    const r = scorePair(makeProfile({ presentation_role: "lead" }), makeProfile({ presentation_role: "behind_scenes" }));
    expect(r.score).toBe(2);
    expect(r.reasons[0]).toMatch(/presenting/);
  });

  it("caps shared info styles at +2", () => {
    const all = ["written", "visual", "verbal", "demonstration"];
    const r = scorePair(makeProfile({ info_styles: all }), makeProfile({ info_styles: all }));
    expect(r.score).toBe(2);
  });
});

describe("privacy in matching", () => {
  it("ignores a field when either student made it private", () => {
    const a = makeProfile({ communication: "text", visibility: { communication: "private" } });
    const b = makeProfile({ communication: "text" });
    expect(scorePair(a, b)).toEqual({ score: 0, reasons: [] });
    expect(scorePair(b, a)).toEqual({ score: 0, reasons: [] });
  });

  it("uses 'after_match' answers for scoring but never explains them", () => {
    // processing_time defaults to after_match
    const a = makeProfile({ processing_time: "take_time" });
    const b = makeProfile({ processing_time: "take_time" });
    const r = scorePair(a, b);
    expect(r.score).toBe(1);
    expect(r.reasons).toEqual([]);
  });

  it("explains a field only when both made it public", () => {
    const a = makeProfile({ pacing: "checkins" });
    const b = makeProfile({ pacing: "checkins", visibility: { pacing: "after_match" } });
    const r = scorePair(a, b);
    expect(r.score).toBe(2);
    expect(r.reasons).toEqual([]);
  });

  it("toPublicProfile only shows public fields", () => {
    const p = makeProfile({
      communication: "text",
      cool_down: "step_away", // after_match by default
      pacing: "flexible",
      visibility: { pacing: "private" },
    });
    const pub = toPublicProfile(p);
    expect(pub.communication).toBe("text");
    expect(pub).not.toHaveProperty("cool_down");
    expect(pub).not.toHaveProperty("pacing");
    expect(pub).not.toHaveProperty("visibility");
  });
});

describe("topMatches", () => {
  it("excludes yourself, sorts best first, and limits the count", () => {
    const me = makeProfile({ communication: "text", pacing: "checkins" });
    const great = makeProfile({ communication: "text", pacing: "checkins" });
    const ok = makeProfile({ communication: "text" });
    const bad = makeProfile({ communication: "voice", pacing: "flexible" });
    const result = topMatches(me, [me, bad, ok, great], 2);
    expect(result.map((m) => m.hero.user_id)).toEqual([great.user_id, ok.user_id]);
  });

  it("never leaks private or after_match answers in results", () => {
    const me = makeProfile({ communication: "text" });
    const other = makeProfile({ communication: "text", cool_down: "step_away", feedback_style: "gentle" });
    const [m] = topMatches(me, [other]);
    expect(m.hero).not.toHaveProperty("cool_down");
    expect(m.hero).not.toHaveProperty("feedback_style");
  });
});
