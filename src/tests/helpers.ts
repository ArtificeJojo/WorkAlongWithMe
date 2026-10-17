import type { Profile } from "@/lib/matching";

// Builds a full profile for tests; override only what a test cares about.
export function makeProfile(overrides: Partial<Profile> = {}): Profile {
  return {
    user_id: overrides.user_id ?? crypto.randomUUID(),
    display_name: "Test",
    hero_name: "Test Hero",
    avatar: "fox",
    task_format: null,
    task_size: null,
    pacing: null,
    info_styles: [],
    roles: [],
    communication: null,
    processing_time: null,
    feedback_style: null,
    cool_down: null,
    presentation_role: null,
    visibility: {},
    completed_quests: [],
    ...overrides,
  };
}
