"""Quests: the story scenes students play, and saving their answers to Tiger Data.

Two tracks, played in order:
  gators  -> Kanban Swamp with Chomp the Gator (how you handle work)
  turtle  -> Ping Pond with Ponder the Turtle (how you communicate), unlocked by finishing gators

Every scene fills one column of the `profiles` table. The page (src/quest.html) gets
these definitions as JSON, so the story text and the database values never drift apart.
"""

import json
from os import environ as env

import asyncpg

# ------------------------------------------------------------------ quest definitions

GATORS = {
    "id": "gators",
    "name": "Kanban Swamp: The Great Swamp Launch",
    "guide": "Chomp",
    "character": "chomp",
    "badge": "Swamp Launcher",
    "badge_emoji": "🐊",
    "card": "Help Chomp launch SwampBook before sundown, and discover how you like to tackle work.",
    "intro": {
        "line": "Uh-oh. SwampBook launches at sundown, and the swamp is FLOODED with tangled code blocks. "
        "Help a gator out?",
        "button": "Let's wade in!",
    },
    "scenes": [
        {
            "id": "powers",
            "title": "Choose Your Powers",
            "field": "roles",
            "multi": 2,
            "line": "First things first: every hero has powers. Which ones are yours? Pick up to two.",
            "choices": [
                {"value": "builder", "emoji": "🔨", "label": "Builder", "reaction": "Your power glows a deep blue. Swamp-tastic!"},
                {"value": "designer", "emoji": "🎨", "label": "Designer", "reaction": "Your power sparkles in every color!"},
                {"value": "researcher", "emoji": "🔍", "label": "Researcher", "reaction": "A tiny magnifying glass appears. Ooh, clues!"},
                {"value": "presenter", "emoji": "🎤", "label": "Presenter", "reaction": "Your power hums a little fanfare!"},
                {"value": "leader", "emoji": "👑", "label": "Leader", "reaction": "Your power forms a tiny crown!"},
            ],
        },
        {
            "id": "workbench",
            "title": "Build Your Workbench",
            "field": "task_format",
            "line": "Every hero needs a workbench. Which tool goes front and center?",
            "choices": [
                {"value": "list", "emoji": "📜", "label": "A giant scroll with everything on it", "reaction": "The scroll unrolls across the whole bench. Chomp whistles."},
                {"value": "cards", "emoji": "🧩", "label": "Sticky-note blocks I can move around", "reaction": "Colorful blocks snap onto the bench. Click-click-click!"},
                {"value": "checklist", "emoji": "✅", "label": "A checklist, one step at a time", "reaction": "A shiny clipboard lands on the bench. Ding!"},
            ],
        },
        {
            "id": "mega_bug",
            "title": "MEGA-BUG Rises!",
            "field": "task_size",
            "line": "WHOA! MEGA-BUG just rose out of the swamp, and it's eating the launch schedule! How do we beat it?",
            "choices": [
                {"value": "large", "emoji": "⚔️", "label": "Take it on all at once", "reaction": "POWER ATTACK! MEGA-BUG launches into the sky like a firework. BIG MOVES!"},
                {"value": "bite_sized", "emoji": "✂️", "label": "Slice it into tiny bugs", "reaction": "MEGA-BUG splits into five tiny bugs. They salute and waddle off. Way less scary in pieces!"},
            ],
        },
        {
            "id": "launch_bridge",
            "title": "The Launch Bridge",
            "field": "pacing",
            "line": "The launch pad is across the swamp. How should we build the bridge?",
            "choices": [
                {"value": "single_deadline", "emoji": "🌉", "label": "All at once, right before sundown", "reaction": "WHOOSH! The whole bridge appears just in time."},
                {"value": "checkins", "emoji": "🪵", "label": "One plank at a time, checking in", "reaction": "Plank... plank... plank. A sturdy bridge, step by step."},
                {"value": "flexible", "emoji": "🪢", "label": "Whenever it feels right", "reaction": "A bouncy rope bridge swings into place. Chomp does a little hop."},
            ],
        },
        {
            "id": "locked_gate",
            "title": "The Locked Gate",
            "field": "info_styles",
            "multi": 1,
            "line": "The server gate is locked by a tricky puzzle! Want a hint? Pick the kind that helps you most.",
            "choices": [
                {"value": "written", "emoji": "✍️", "label": "A written clue", "reaction": "A note floats down. You read it, and the gate clicks open!"},
                {"value": "visual", "emoji": "🖼️", "label": "A diagram", "reaction": "A glowing map appears. You trace it, and the gate clicks open!"},
                {"value": "verbal", "emoji": "🗣️", "label": "Chomp explains it", "reaction": "Chomp talks it through. You nod, and the gate clicks open!"},
                {"value": "demonstration", "emoji": "👀", "label": "Chomp shows me step by step", "reaction": "Chomp does the first step, you do the rest. The gate clicks open!"},
            ],
        },
    ],
    "finale": "SwampBook is LIVE! Chomp-a-doodle! You're an official Swamp Launcher.",
}

TURTLE = {
    "id": "turtle",
    "name": "Ping Pond: The Pond Fair",
    "guide": "Ponder",
    "character": "ponder",
    "badge": "Pond Keeper",
    "badge_emoji": "🐢",
    "card": "Help Ponder the Turtle calm the noisy Ping Pond, and set the rules for how your team talks.",
    "intro": {
        "line": "Hello... there... friend. No rush. The Ping Pond is a little noisy today, and the Pond Fair is tonight. "
        "Will you help me?",
        "button": "Let's float in!",
    },
    "scenes": [
        {
            "id": "message_flood",
            "title": "The Message Flood",
            "field": "communication",
            "line": "The pond is flooded with bottles, croaks and splashes! How should the pond send word to you?",
            "choices": [
                {"value": "text", "emoji": "📜", "label": "Message bottles (group chat)", "reaction": "The bottles line up neatly by the shore. So calm."},
                {"value": "voice", "emoji": "📞", "label": "Croak calls (voice calls)", "reaction": "The frogs tune their croaks into tidy little calls."},
                {"value": "in_person", "emoji": "🚶", "label": "Swim over and find me (in person)", "reaction": "Ponder paddles over for a friendly face-to-face."},
                {"value": "mix", "emoji": "🔀", "label": "A mix of everything", "reaction": "Bottles, croaks and visits all find their place."},
            ],
        },
        {
            "id": "slow_riddle",
            "title": "The Slow Riddle",
            "field": "processing_time",
            "line": "I have a riddle for you... Should the pond wait for your answer?",
            "choices": [
                {"value": "instant", "emoji": "⚡", "label": "Keep it quick, I like fast replies", "reaction": "Zip! The riddle scroll snaps shut. Quick thinker!"},
                {"value": "take_time", "emoji": "⏳", "label": "Give me time to think and finish", "reaction": "An hourglass appears and the whole pond waits patiently. Ponder approves."},
            ],
        },
        {
            "id": "frog_bug",
            "title": "The Frog's Bug Report",
            "field": "feedback_style",
            "line": "Freddie the Frog found a bug in my lily-pad app. If there's a bug in your work, how should we tell you?",
            "choices": [
                {"value": "direct", "emoji": "🎯", "label": "Tell me straight", "reaction": "Freddie hops up with a clear, honest note. Nice and simple."},
                {"value": "gentle", "emoji": "🌸", "label": "Kindly, with a smile", "reaction": "Freddie brings the note with a little flower. Aww."},
                {"value": "written", "emoji": "✍️", "label": "Write it down for me", "reaction": "Freddie leaves a neat note on a lily pad."},
                {"value": "private", "emoji": "🤫", "label": "Just between us", "reaction": "Freddie whispers it quietly, just for you."},
            ],
        },
        {
            "id": "rainstorm",
            "title": "The Rainstorm",
            "field": "cool_down",
            "line": "A storm rolls in: wind, rain, everyone talking at once! When things get too much, what should happen?",
            "choices": [
                {"value": "break_signal", "emoji": "🚩", "label": "I raise my flag for a break", "reaction": "Up goes the flag, and the whole pond pauses. The storm passes."},
                {"value": "step_away", "emoji": "🐚", "label": "I tuck into my shell for a bit", "reaction": "Shell time! The storm passes while you rest."},
                {"value": "switch_to_text", "emoji": "📜", "label": "Switch to writing", "reaction": "Everyone switches to message bottles. Quiet again."},
                {"value": "none", "emoji": "😎", "label": "I'm good, I can ride it out", "reaction": "You surf the waves like a pro. The storm passes."},
            ],
        },
        {
            "id": "pond_fair",
            "title": "The Pond Fair",
            "field": "presentation_role",
            "line": "The Pond Fair is starting! How do you want to be part of the big demo?",
            "choices": [
                {"value": "lead", "emoji": "👑", "label": "Lead the presentation", "reaction": "Spotlight on you! The pond cheers."},
                {"value": "short_part", "emoji": "🎤", "label": "A short part", "reaction": "A quick, shining moment. Perfect."},
                {"value": "behind_scenes", "emoji": "🛠️", "label": "Run the demo behind the scenes", "reaction": "You pull the lever and the demo runs flawlessly. Backstage hero!"},
            ],
        },
    ],
    "finale": "The pond is calm and the Pond Fair is a hit. You're an official Pond Keeper. Take a bow... slowly.",
}

QUESTS = {GATORS["id"]: GATORS, TURTLE["id"]: TURTLE}
QUEST_ORDER = ["gators", "turtle"]

# Every value the database accepts, per profiles column.
ALLOWED = {
    "task_format": ["list", "cards", "checklist"],
    "task_size": ["large", "bite_sized"],
    "pacing": ["single_deadline", "checkins", "flexible"],
    "info_styles": ["written", "visual", "verbal", "demonstration"],
    "roles": ["leader", "builder", "researcher", "designer", "presenter"],
    "communication": ["text", "voice", "in_person", "mix"],
    "processing_time": ["instant", "take_time"],
    "feedback_style": ["direct", "gentle", "written", "private"],
    "cool_down": ["break_signal", "step_away", "switch_to_text", "none"],
    "presentation_role": ["lead", "short_part", "behind_scenes"],
}
LIST_FIELDS = {"info_styles", "roles"}
LIST_MAX = {"info_styles": 2, "roles": 2}
FIELDS = list(ALLOWED)
VISIBILITY_VALUES = {"public", "after_match", "private"}

# More personal answers stay hidden until a group forms, unless the student changes it.
DEFAULT_VISIBILITY = {
    "task_format": "public",
    "task_size": "public",
    "pacing": "public",
    "info_styles": "public",
    "roles": "public",
    "communication": "public",
    "processing_time": "after_match",
    "feedback_style": "after_match",
    "cool_down": "after_match",
    "presentation_role": "public",
}


class QuestError(Exception):
    pass


def check_answer(field, value):
    """Returns an error message, or None if the value is a real choice (None = skipped scene)."""
    if field not in ALLOWED:
        return f"Unknown question: {field}"
    allowed = ALLOWED[field]
    if field in LIST_FIELDS:
        if not isinstance(value, list):
            return f"{field} must be a list"
        if len(value) > LIST_MAX[field]:
            return f"{field} allows at most {LIST_MAX[field]} picks"
        if len(set(value)) != len(value):
            return f"{field} has duplicate picks"
        bad = [v for v in value if v not in allowed]
        return f"{field} has an unknown choice" if bad else None
    if value is None:
        return None
    return None if isinstance(value, str) and value in allowed else f"{field} has an unknown choice"


def summarize(quest, answers):
    """Friendly 'You do your best work when...' lines for the mirror, in scene order."""
    lines = []
    for scene in quest["scenes"]:
        value = answers.get(scene["field"])
        picked = value if isinstance(value, list) else ([value] if value else [])
        labels = [f"{c['emoji']} {c['label']}" for p in picked for c in scene["choices"] if c["value"] == p]
        if labels:
            lines.append({"title": scene["title"], "field": scene["field"], "text": " + ".join(labels)})
    return lines


def to_script_json(value):
    """JSON that is safe to drop inside a <script> tag."""
    return json.dumps(value).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def quests_json():
    """Quest definitions for the browser."""
    return to_script_json({"quests": QUESTS, "order": QUEST_ORDER, "defaultVisibility": DEFAULT_VISIBILITY})


# ------------------------------------------------------------------ database

async def _connect():
    return await asyncpg.connect(env.get("DATABASE_URL"))


async def get_progress(auth0_sub):
    """Which quests this student finished, plus their saved answers and privacy choices."""
    conn = await _connect()
    try:
        row = await conn.fetchrow(
            "SELECT u.id, p.completed_quests, p.visibility, "
            + ", ".join(f"p.{f}" for f in FIELDS)
            + " FROM users u LEFT JOIN profiles p ON p.user_id = u.id WHERE u.auth0_sub = $1",
            auth0_sub,
        )
    finally:
        await conn.close()
    if not row:
        return None
    completed = list(row["completed_quests"] or [])
    visibility = row["visibility"]
    if isinstance(visibility, str):
        visibility = json.loads(visibility)
    return {
        "user_id": str(row["id"]),
        "completed": completed,
        "answers": {f: (list(row[f]) if f in LIST_FIELDS and row[f] is not None else row[f]) for f in FIELDS},
        "visibility": visibility or {},
        "unlocked": unlocked_quests(completed),
    }


def unlocked_quests(completed):
    """Gators is always open; each later quest opens once the one before it is done."""
    unlocked = []
    for i, quest_id in enumerate(QUEST_ORDER):
        if i == 0 or QUEST_ORDER[i - 1] in completed:
            unlocked.append(quest_id)
    return unlocked


def next_quest(completed):
    """The first quest not finished yet, or None when all are done."""
    return next((q for q in QUEST_ORDER if q not in completed), None)


async def finish_quest(auth0_sub, quest_id, answers, visibility):
    """Validate and save one quest's answers + privacy choices, and award its badge.
    Raises QuestError for anything invalid. Returns the updated progress."""
    quest = QUESTS.get(quest_id)
    if not quest:
        raise QuestError("Unknown quest")
    if not isinstance(answers, dict) or not isinstance(visibility or {}, dict):
        raise QuestError("Answers must be an object")

    # Only this quest's own questions can be saved here.
    quest_fields = [s["field"] for s in quest["scenes"]]
    fields = [f for f in quest_fields if f in answers]
    for f in fields:
        problem = check_answer(f, answers[f])
        if problem:
            raise QuestError(problem)
    vis = {k: v for k, v in (visibility or {}).items() if k in quest_fields and v in VISIBILITY_VALUES}

    progress = await get_progress(auth0_sub)
    if not progress:
        raise QuestError("Hero not found")
    if quest_id not in progress["unlocked"]:
        raise QuestError("Finish the quest before this one first")

    cols = ["user_id", *fields, "visibility", "completed_quests"]
    values = [progress["user_id"], *[answers[f] for f in fields], json.dumps(vis), [quest_id]]
    placeholders = [f"${i + 1}" for i in range(len(cols))]
    placeholders[0] += "::uuid"
    placeholders[-2] += "::jsonb"
    placeholders[-1] += "::text[]"
    updates = [f"{f} = EXCLUDED.{f}" for f in fields] + [
        "visibility = profiles.visibility || EXCLUDED.visibility",
        "completed_quests = ARRAY(SELECT DISTINCT unnest(profiles.completed_quests || EXCLUDED.completed_quests))",
        "updated_at = now()",
    ]
    conn = await _connect()
    try:
        async with conn.transaction():
            await conn.execute(
                f"INSERT INTO profiles ({', '.join(cols)}) VALUES ({', '.join(placeholders)}) "
                f"ON CONFLICT (user_id) DO UPDATE SET {', '.join(updates)}",
                *values,
            )
    finally:
        await conn.close()
    return await get_progress(auth0_sub)
