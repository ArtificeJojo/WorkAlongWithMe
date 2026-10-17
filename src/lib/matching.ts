// Rule-based matching. Rules pick the matches; Gemini only explains them later.

export type Visibility = "public" | "after_match" | "private";

export const PROFILE_FIELDS = [
  "task_format",
  "task_size",
  "pacing",
  "info_styles",
  "roles",
  "communication",
  "processing_time",
  "feedback_style",
  "cool_down",
  "presentation_role",
] as const;

export type Field = (typeof PROFILE_FIELDS)[number];
export const ARRAY_FIELDS: Field[] = ["info_styles", "roles"];

export type Profile = {
  user_id: string;
  display_name: string;
  hero_name: string | null;
  avatar: string | null;
  task_format: string | null;
  task_size: string | null;
  pacing: string | null;
  info_styles: string[];
  roles: string[];
  communication: string | null;
  processing_time: string | null;
  feedback_style: string | null;
  cool_down: string | null;
  presentation_role: string | null;
  visibility: Partial<Record<Field, Visibility>>;
  completed_quests: string[];
};

// Used when a student hasn't set privacy for a field.
// More personal answers default to "after_match".
export const DEFAULT_VISIBILITY: Record<Field, Visibility> = {
  task_format: "public",
  task_size: "public",
  pacing: "public",
  info_styles: "public",
  roles: "public",
  communication: "public",
  processing_time: "after_match",
  feedback_style: "after_match",
  cool_down: "after_match",
  presentation_role: "public",
};

export function visibilityOf(p: Profile, f: Field): Visibility {
  return p.visibility?.[f] ?? DEFAULT_VISIBILITY[f];
}

const LABELS: Record<string, string> = {
  text: "text-first",
  voice: "voice",
  in_person: "in-person",
  mix: "mixed",
  checkins: "small check-ins along the way",
  single_deadline: "one final deadline",
  flexible: "flexible timing",
  cards: "visual task cards",
  list: "one long list",
  checklist: "step-by-step checklists",
  bite_sized: "bite-sized tasks",
  large: "big chunks of work",
  written: "written",
  visual: "visual",
  verbal: "spoken",
  demonstration: "show-me-by-example",
  leader: "leader",
  builder: "builder",
  researcher: "researcher",
  designer: "designer",
  presenter: "presenter",
};
const label = (v: string) => LABELS[v] ?? v;

const listJoin = (items: string[]) =>
  items.length <= 1
    ? items.join("")
    : `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;

export type ScoredPair = { score: number; reasons: string[] };

export function scorePair(me: Profile, them: Profile): ScoredPair {
  let score = 0;
  const reasons: string[] = [];

  // A field counts for matching unless either person made it private.
  const usable = (f: Field) =>
    visibilityOf(me, f) !== "private" && visibilityOf(them, f) !== "private";
  // A reason is only written if both people made that field public,
  // so "after_match" answers never leak through the explanation.
  const sayable = (f: Field) =>
    visibilityOf(me, f) === "public" && visibilityOf(them, f) === "public";
  const add = (pts: number, f: Field, why?: string) => {
    score += pts;
    if (pts > 0 && why && sayable(f)) reasons.push(why);
  };

  // Communication (weighted highest: biggest source of group friction)
  if (usable("communication") && me.communication && them.communication) {
    const a = me.communication, b = them.communication;
    if (a === b) add(3, "communication", `You both prefer ${label(a)} communication`);
    else if (a === "mix" || b === "mix") add(1, "communication", "Your communication styles can flex to fit each other");
    else if ((a === "text" && b === "voice") || (a === "voice" && b === "text")) add(-2, "communication");
  }

  // Pacing
  if (usable("pacing") && me.pacing && them.pacing) {
    if (me.pacing === them.pacing) add(2, "pacing", `You both like ${label(me.pacing)}`);
    else if (
      (me.pacing === "checkins" && them.pacing === "flexible") ||
      (me.pacing === "flexible" && them.pacing === "checkins")
    ) add(-1, "pacing");
  }

  // Processing time
  if (usable("processing_time") && me.processing_time && them.processing_time) {
    if (me.processing_time === them.processing_time) add(1, "processing_time", "You move at a similar pace in conversations");
    else add(-1, "processing_time");
  }

  // Task format and size
  if (usable("task_format") && me.task_format && me.task_format === them.task_format)
    add(1, "task_format", `You both organize work with ${label(me.task_format)}`);
  if (usable("task_size") && me.task_size && me.task_size === them.task_size)
    add(1, "task_size", `You both prefer ${label(me.task_size)}`);

  // Shared ways of taking in information (cap +2)
  if (usable("info_styles")) {
    const shared = me.info_styles.filter((s) => them.info_styles.includes(s));
    if (shared.length)
      add(Math.min(shared.length, 2), "info_styles", `You both like ${listJoin(shared.map(label))} instructions`);
  }

  // Complementary roles: reward what they bring that you don't (cap +4)
  if (usable("roles")) {
    const newRoles = them.roles.filter((r) => !me.roles.includes(r));
    if (newRoles.length)
      add(Math.min(newRoles.length * 2, 4), "roles", `They bring ${listJoin(newRoles.map(label))} skills to the group`);
  }

  // Presentation roles: a presenter + a behind-the-scenes person is ideal
  if (usable("presentation_role") && me.presentation_role && them.presentation_role) {
    const pair = [me.presentation_role, them.presentation_role].sort().join("+");
    if (pair === "behind_scenes+lead")
      add(2, "presentation_role", "One of you loves presenting and the other shines behind the scenes");
    else if (me.presentation_role === "short_part" || them.presentation_role === "short_part")
      add(1, "presentation_role", "Your presentation styles fit together");
    else if (pair === "behind_scenes+behind_scenes") add(-1, "presentation_role");
  }

  return { score, reasons };
}

// What other students are allowed to see before a group forms.
export type PublicProfile = {
  user_id: string;
  display_name: string;
  hero_name: string | null;
  avatar: string | null;
} & Partial<Record<Field, string | string[] | null>>;

export function toPublicProfile(p: Profile): PublicProfile {
  const out: PublicProfile = {
    user_id: p.user_id,
    display_name: p.display_name,
    hero_name: p.hero_name,
    avatar: p.avatar,
  };
  for (const f of PROFILE_FIELDS) {
    if (visibilityOf(p, f) === "public") out[f] = p[f];
  }
  return out;
}

export type Match = { hero: PublicProfile; score: number; reasons: string[] };

export function topMatches(me: Profile, others: Profile[], n = 3): Match[] {
  return others
    .filter((o) => o.user_id !== me.user_id)
    .map((o) => ({ hero: toPublicProfile(o), ...scorePair(me, o) }))
    .sort((a, b) => b.score - a.score)
    .slice(0, n);
}
