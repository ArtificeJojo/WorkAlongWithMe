// Browser-side helpers for the game screens. Call finishQuest() on the finale.

import type { Field, Visibility } from "./matching";

const HERO_KEY = "heroId";

export function getHeroId(): string | null {
  try {
    return localStorage.getItem(HERO_KEY);
  } catch {
    return null;
  }
}

function setHeroId(id: string) {
  try {
    localStorage.setItem(HERO_KEY, id);
  } catch {
    /* storage blocked: the hero still saves, it just won't be remembered */
  }
}

type FinishArgs = {
  questId: string;
  answers: Partial<Record<Field, string | string[] | null>>;
  visibility?: Partial<Record<Field, Visibility>>;
  // Only needed the first time a hero is created:
  displayName?: string;
  heroName?: string;
  avatar?: string;
};

// Saves every answer from a quest in one call and awards its badge.
// Returns the saved profile, or throws with a friendly message.
export async function finishQuest(args: FinishArgs) {
  const userId = getHeroId();
  const res = await fetch("/api/profile", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      userId: userId ?? undefined,
      displayName: args.displayName,
      heroName: args.heroName,
      avatar: args.avatar,
      answers: args.answers,
      visibility: args.visibility,
      completedQuest: args.questId,
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error ?? "Couldn't save your quest. Try again?");
  setHeroId(data.profile.user_id);
  return data.profile;
}
