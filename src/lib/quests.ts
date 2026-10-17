// Quest definitions: the single source of truth for what each scene asks
// and which database value each choice saves. The game screens read this,
// and the API uses it to reject anything that isn't a real choice.

import type { Field } from "./matching";

export type Choice = { value: string; label: string; emoji: string; reaction: string };
export type Scene = {
  id: string;
  title: string;
  field: Field;
  multi?: number; // max picks for multi-select scenes (default: pick one)
  speaker: string;
  line: string;
  choices: Choice[];
  checkIn?: string; // optional gut-check question after the reaction
};
export type Quest = {
  id: string;
  name: string;
  badge: string;
  intro: { speaker: string; line: string; button: string };
  scenes: Scene[];
  finale: { speaker: string; line: string };
};

// 🐊 Kanban Swamp: how you handle work.
// For every student; especially helpful for students with ADHD.
// Code-flavored story, but no coding knowledge needed.
export const KANBAN_SWAMP: Quest = {
  id: "kanban_swamp",
  name: "Kanban Swamp: The Great Swamp Launch",
  badge: "Swamp Launcher",
  intro: {
    speaker: "Chomp",
    line: "Uh-oh. SwampBook launches at sundown, and the swamp is FLOODED with tangled code blocks. Help a gator out?",
    button: "Let's wade in!",
  },
  scenes: [
    {
      id: "workbench",
      title: "Build Your Workbench",
      field: "task_format",
      speaker: "Chomp",
      line: "First, every hero needs a workbench. Which tool goes front and center?",
      choices: [
        { value: "list", emoji: "📜", label: "A giant scroll with everything on it", reaction: "The scroll unrolls across the whole bench. Chomp whistles." },
        { value: "cards", emoji: "🧩", label: "Sticky-note blocks I can move around", reaction: "Colorful blocks snap onto the bench. Click-click-click!" },
        { value: "checklist", emoji: "✅", label: "A checklist, one step at a time", reaction: "A shiny clipboard lands on the bench. Ding!" },
      ],
    },
    {
      id: "mega_bug",
      title: "MEGA-BUG Rises!",
      field: "task_size",
      speaker: "Chomp",
      line: "WHOA! MEGA-BUG just rose out of the swamp, and it's eating the launch schedule! How do we beat it?",
      choices: [
        { value: "large", emoji: "⚔️", label: "Take it on all at once", reaction: "POWER ATTACK! MEGA-BUG launches into the sky like a firework. \"BIG MOVES!\"" },
        { value: "bite_sized", emoji: "✂️", label: "Slice it into tiny bugs", reaction: "MEGA-BUG splits into five tiny bugs. They salute and waddle off. \"Way less scary in pieces!\"" },
      ],
      checkIn: "Does that match how you like to tackle big work?",
    },
    {
      id: "launch_bridge",
      title: "The Launch Bridge",
      field: "pacing",
      speaker: "Chomp",
      line: "The launch pad is across the swamp. How should we build the bridge?",
      choices: [
        { value: "single_deadline", emoji: "🌉", label: "All at once, right before sundown", reaction: "WHOOSH! The whole bridge appears just in time." },
        { value: "checkins", emoji: "🪵", label: "One plank at a time, checking in", reaction: "Plank... plank... plank. A sturdy bridge, step by step." },
        { value: "flexible", emoji: "🪢", label: "Whenever it feels right", reaction: "A bouncy rope bridge swings into place. Chomp does a little hop." },
      ],
    },
    {
      id: "locked_gate",
      title: "The Locked Gate",
      field: "info_styles",
      multi: 1,
      speaker: "Chomp",
      line: "The server gate is locked by a tricky puzzle! Want a hint? Pick the kind that helps you most.",
      choices: [
        { value: "written", emoji: "✍️", label: "A written clue", reaction: "A note floats down. You read it, and the gate clicks open!" },
        { value: "visual", emoji: "🖼️", label: "A diagram", reaction: "A glowing map appears. You trace it, and the gate clicks open!" },
        { value: "verbal", emoji: "🗣️", label: "Chomp explains it", reaction: "Chomp talks it through. You nod, and the gate clicks open!" },
        { value: "demonstration", emoji: "👀", label: "Chomp shows me step by step", reaction: "Chomp does the first step, you do the rest. The gate clicks open!" },
      ],
    },
  ],
  finale: { speaker: "Chomp", line: "SwampBook is LIVE! You're an official Swamp Launcher." },
};

// Hero setup, before the quests: "Choose your powers".
// Roles live here (not in a quest) because matching needs them for everyone.
export const CHOOSE_POWERS: Scene = {
  id: "choose_powers",
  title: "Choose Your Powers",
  field: "roles",
  multi: 2,
  speaker: "Chomp",
  line: "Every hero has powers. Which ones are yours? Pick up to two.",
  choices: [
    { value: "builder", emoji: "🔨", label: "Builder", reaction: "Your power glows a deep blue." },
    { value: "designer", emoji: "🎨", label: "Designer", reaction: "Your power sparkles in every color." },
    { value: "researcher", emoji: "🔍", label: "Researcher", reaction: "Your power shows a tiny magnifying glass." },
    { value: "presenter", emoji: "🎤", label: "Presenter", reaction: "Your power hums a little fanfare." },
    { value: "leader", emoji: "👑", label: "Leader", reaction: "Your power forms a tiny crown." },
  ],
};

export const QUESTS: Record<string, Quest> = { [KANBAN_SWAMP.id]: KANBAN_SWAMP };

// Every allowed database value, per field. Ping Pond Castle's fields are listed
// here too so its screens can save before its quest definition is written.
export const ALLOWED: Record<Field, string[]> = {
  task_format: ["list", "cards", "checklist"],
  task_size: ["large", "bite_sized"],
  pacing: ["single_deadline", "checkins", "flexible"],
  info_styles: ["written", "visual", "verbal", "demonstration"],
  roles: ["leader", "builder", "researcher", "designer", "presenter"],
  communication: ["text", "voice", "in_person", "mix"],
  processing_time: ["instant", "take_time"],
  feedback_style: ["direct", "gentle", "written", "private"],
  cool_down: ["break_signal", "step_away", "switch_to_text", "none"],
  presentation_role: ["lead", "short_part", "behind_scenes"],
};

// Most picks the API accepts for list fields (a scene may allow fewer).
const MULTI_MAX: Partial<Record<Field, number>> = { info_styles: 2, roles: 2 };

// Returns an error message, or null if the answer is a real choice.
export function checkAnswer(field: Field, value: unknown): string | null {
  const allowed = ALLOWED[field];
  if (field in MULTI_MAX) {
    if (!Array.isArray(value)) return `${field} must be a list`;
    if (value.length > MULTI_MAX[field]!) return `${field} allows at most ${MULTI_MAX[field]} picks`;
    if (new Set(value).size !== value.length) return `${field} has duplicate picks`;
    const bad = value.find((v) => !allowed.includes(v as string));
    return bad === undefined ? null : `${field} has an unknown choice: ${String(bad)}`;
  }
  if (value === null) return null; // skipped scene
  return typeof value === "string" && allowed.includes(value) ? null : `${field} has an unknown choice`;
}

// Plain-language lines for the finale's "here's what you picked" card.
export function summarize(quest: Quest, answers: Partial<Record<Field, unknown>>): string[] {
  return quest.scenes.flatMap((s) => {
    const v = answers[s.field];
    const picked = (Array.isArray(v) ? v : v ? [v] : []) as string[];
    const labels = picked
      .map((p) => s.choices.find((c) => c.value === p))
      .filter(Boolean)
      .map((c) => `${c!.emoji} ${c!.label}`);
    return labels.length ? [labels.join(" + ")] : [];
  });
}
