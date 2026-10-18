"""Matching: rules pick the matches (so they're consistent and explainable); Gemini only words them.

Privacy:
  'public'      -> used for matching and shown/explained
  'after_match' -> used for matching, never shown or explained before a group forms
  'private'     -> never used or shown
"""

import json
from os import environ as env

import asyncpg

from quests import DEFAULT_VISIBILITY, FIELDS, LIST_FIELDS

LABELS = {
    "text": "text-first", "voice": "voice", "in_person": "in-person", "mix": "mixed",
    "checkins": "small check-ins along the way", "single_deadline": "one final deadline", "flexible": "flexible timing",
    "cards": "sticky-note task blocks", "list": "one big list", "checklist": "step-by-step checklists",
    "bite_sized": "bite-sized tasks", "large": "big chunks of work",
    "written": "written", "visual": "visual", "verbal": "spoken", "demonstration": "show-me-by-example",
    "leader": "leader", "builder": "builder", "researcher": "researcher", "designer": "designer", "presenter": "presenter",
}


def label(v):
    return LABELS.get(v, v)


def list_join(items):
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


def visibility_of(p, field):
    return (p.get("visibility") or {}).get(field) or DEFAULT_VISIBILITY[field]


def score_pair(me, them):
    """Returns (score, reasons). Reasons only mention fields BOTH students made public."""
    score = 0
    reasons = []

    def usable(f):
        return visibility_of(me, f) != "private" and visibility_of(them, f) != "private"

    def add(points, f, why=None):
        nonlocal score
        score += points
        if points > 0 and why and visibility_of(me, f) == "public" and visibility_of(them, f) == "public":
            reasons.append(why)

    a, b = me.get("communication"), them.get("communication")
    if usable("communication") and a and b:
        if a == b:
            add(3, "communication", f"You both prefer {label(a)} communication")
        elif "mix" in (a, b):
            add(1, "communication", "Your communication styles can flex to fit each other")
        elif {a, b} == {"text", "voice"}:
            add(-2, "communication")

    a, b = me.get("pacing"), them.get("pacing")
    if usable("pacing") and a and b:
        if a == b:
            add(2, "pacing", f"You both like {label(a)}")
        elif {a, b} == {"checkins", "flexible"}:
            add(-1, "pacing")

    a, b = me.get("processing_time"), them.get("processing_time")
    if usable("processing_time") and a and b:
        add(1 if a == b else -1, "processing_time", "You move at a similar pace in conversations")

    if usable("task_format") and me.get("task_format") and me.get("task_format") == them.get("task_format"):
        add(1, "task_format", f"You both organize work with {label(me['task_format'])}")
    if usable("task_size") and me.get("task_size") and me.get("task_size") == them.get("task_size"):
        add(1, "task_size", f"You both prefer {label(me['task_size'])}")

    if usable("info_styles"):
        shared = [s for s in me.get("info_styles") or [] if s in (them.get("info_styles") or [])]
        if shared:
            add(min(len(shared), 2), "info_styles", f"You both like {list_join([label(s) for s in shared])} instructions")

    if usable("roles"):
        new_roles = [r for r in them.get("roles") or [] if r not in (me.get("roles") or [])]
        if new_roles:
            add(min(len(new_roles) * 2, 4), "roles", f"They bring {list_join([label(r) for r in new_roles])} skills to the group")

    a, b = me.get("presentation_role"), them.get("presentation_role")
    if usable("presentation_role") and a and b:
        pair = tuple(sorted((a, b)))
        if pair == ("behind_scenes", "lead"):
            add(2, "presentation_role", "One of you loves presenting and the other shines behind the scenes")
        elif "short_part" in pair:
            add(1, "presentation_role", "Your presentation styles fit together")
        elif pair == ("behind_scenes", "behind_scenes"):
            add(-1, "presentation_role")

    return score, reasons


def public_profile(p):
    """What other students may see before a group forms."""
    out = {k: p[k] for k in ("user_id", "display_name", "completed_quests", "is_demo")}
    for f in FIELDS:
        if visibility_of(p, f) == "public" and p.get(f) not in (None, []):
            out[f] = p[f]
    return out


def top_matches(me, others, n=3):
    scored = []
    for o in others:
        if o["user_id"] == me["user_id"]:
            continue
        score, reasons = score_pair(me, o)
        scored.append({"hero": public_profile(o), "score": score, "reasons": reasons})
    scored.sort(key=lambda m: m["score"], reverse=True)
    return scored[:n]


# ------------------------------------------------------------------ database

SELECT = (
    "SELECT u.id AS user_id, u.display_name, u.is_demo, u.auth0_sub, p.visibility, p.completed_quests, "
    + ", ".join(f"p.{f}" for f in FIELDS)
    + " FROM users u JOIN profiles p ON p.user_id = u.id"
)


def _row(r):
    d = dict(r)
    d["user_id"] = str(d["user_id"])
    if isinstance(d.get("visibility"), str):
        d["visibility"] = json.loads(d["visibility"])
    d["visibility"] = d.get("visibility") or {}
    d["completed_quests"] = list(d.get("completed_quests") or [])
    for f in LIST_FIELDS:
        d[f] = list(d[f] or [])
    return d


async def get_all_profiles():
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        rows = await conn.fetch(SELECT)
    finally:
        await conn.close()
    return [_row(r) for r in rows]


async def matches_for(auth0_sub, n=3):
    """(me, matches) for a logged-in student, or (None, []) if they haven't played a quest yet.
    Blocked users (either direction) never appear."""
    profiles = await get_all_profiles()
    me = next((p for p in profiles if p["auth0_sub"] == auth0_sub), None)
    if not me:
        return None, []
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        blocked = await conn.fetch(
            "SELECT blocked_id AS id FROM blocks WHERE blocker_id = $1::uuid "
            "UNION SELECT blocker_id FROM blocks WHERE blocked_id = $1::uuid",
            me["user_id"],
        )
    finally:
        await conn.close()
    blocked_ids = {str(r["id"]) for r in blocked}
    others = [p for p in profiles if p["user_id"] not in blocked_ids]
    return me, top_matches(me, others, n)
