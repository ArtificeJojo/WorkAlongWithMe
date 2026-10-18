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
            "line": "To launch SwampBook, we need a team with powers! Which ones are yours? Pick up to two.",
            "choices": [
                {"value": "builder", "label": "Builder", "reaction": "Builders make ideas real! Watch: block, block, block, and SwampBook grows!"},
                {"value": "designer", "label": "Designer", "reaction": "Designers make it beautiful! Swish, swish, and SwampBook gets its colors!"},
                {"value": "researcher", "label": "Researcher", "reaction": "Researchers find the answers! Your magnifying glass spots the clue we need!"},
                {"value": "presenter", "label": "Presenter", "reaction": "Presenters share the big idea! The whole swamp is listening to you!"},
                {"value": "leader", "label": "Leader", "reaction": "Leaders keep the team together! Everyone follows your flag!"},
            ],
        },
        {
            "id": "workbench",
            "title": "Build Your Workbench",
            "field": "task_format",
            "line": "Next, we plan the launch! A boat just floated our workbench over. Which tool goes front and center?",
            "choices": [
                {"value": "list", "label": "A giant scroll with everything on it", "reaction": "The scroll unrolls across the whole bench. Every launch task, all in one place!"},
                {"value": "cards", "label": "Sticky-note blocks I can move around", "reaction": "Colorful sticky blocks snap onto the board. We move them as launch tasks get done!"},
                {"value": "checklist", "label": "A checklist, one step at a time", "reaction": "A shiny clipboard lands on the bench. One launch step at a time. Ding!"},
            ],
        },
        {
            "id": "mega_bug",
            "title": "The Time Eater Rises!",
            "field": "task_size",
            "line": "The Time Eater gobbled up the launch schedule! We HAVE to stop it! How do we beat it?",
            "choices": [
                {"value": "large", "label": "Take it on all at once", "reaction": "ENERGY BLAST! The Time Eater goes flying, and the launch schedule is safe. BIG MOVES!"},
                {"value": "bite_sized", "label": "Slice it into tiny bugs", "reaction": "Snip, snip! Five tiny bugs scurry away, and the launch schedule is safe. Way less scary in pieces!"},
            ],
        },
        {
            "id": "launch_bridge",
            "title": "The Launch Bridge",
            "field": "pacing",
            "line": "The launch pad is across the swamp. How should we build the bridge?",
            "choices": [
                {"value": "single_deadline", "label": "All at once, right before sundown", "reaction": "Chomp waits... and waits... then WHOOSH! The whole bridge appears just in time!"},
                {"value": "checkins", "label": "One plank at a time, checking in", "reaction": "Plank, check! Plank, check! Chomp builds a sturdy bridge, step by step."},
                {"value": "flexible", "label": "Whenever it feels right", "reaction": "Chomp swings a bouncy rope bridge into place when it feels right. Boing!"},
            ],
        },
        {
            "id": "locked_gate",
            "title": "The Locked Gate",
            "field": "info_styles",
            "multi": 1,
            "line": "The SwampBook server is locked inside the rock mountain! Fill the empty slot on the gate to unlock it. The instructions are tricky... Need a hint? Pick the kind that helps you most.",
            "choices": [
                {"value": "written", "label": "A written clue", "reaction": "A note floats down with a step-by-step checklist. Follow it, then fill the empty slot!"},
                {"value": "visual", "label": "A diagram", "reaction": "The tiles light up in pairs, so you can see what repeats. Now fill the empty slot!"},
                {"value": "verbal", "label": "Chomp explains it", "reaction": "Here's the trick: the colors take turns, blue then red. The shapes take turns too, triangle then circle. So what comes after a blue triangle?"},
                {"value": "demonstration", "label": "Chomp shows me step by step", "reaction": "Watch me tap each tile: blue triangle, red circle. Blue triangle, red circle. See the pattern? Your turn!"},
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
    "card": "Help Ponder the Turtle and Freddie the Frog get their lily-pad app ready for the Pond Fair, and set the rules for how your team talks.",
    "intro": {
        "line": "The Pond Fair is tonight, and our app still needs work... and the pond is so noisy. "
        "Will you help Freddie and me get it ready? No rush...",
        "button": "Let's float in!",
    },
    "scenes": [
        {
            "id": "message_flood",
            "title": "The Message Flood",
            "field": "communication",
            "line": "Step one: app updates are pouring in, and the pond is flooded with bottles, croaks and splashes! How should Freddie and I send app news to you?",
            "choices": [
                {"value": "text", "label": "Message bottles (group chat)", "reaction": "The bottles line up neatly by the shore. App news, nice and calm."},
                {"value": "voice", "label": "Croak calls (voice calls)", "reaction": "Freddie tunes his croaks into tidy little calls about the app."},
                {"value": "in_person", "label": "Swim over and find me (in person)", "reaction": "Ponder paddles over for a friendly face-to-face chat about the app."},
                {"value": "mix", "label": "A mix of everything", "reaction": "Bottles, croaks and visits all find their place. The app news flows."},
            ],
        },
        {
            "id": "slow_riddle",
            "title": "The Slow Riddle",
            "field": "processing_time",
            "line": "Step two: our app greets fair guests with a riddle. Let's test it on you... What has a neck, but no head? Should the app wait for your answer?",
            "choices": [
                {"value": "instant", "label": "Keep it quick, I like fast replies", "reaction": "Zip! Quick thinker! Go ahead, give your answer."},
                {"value": "take_time", "label": "Give me time to think and finish", "reaction": "An hourglass appears, and the whole pond waits patiently. Take all the time you need."},
            ],
        },
        {
            "id": "frog_bug",
            "title": "The Frog's Bug Report",
            "field": "feedback_style",
            "line": "Step three: Freddie tested the app and found a bug, right before the fair. If there's a bug in your work, how should Freddie tell you?",
            "choices": [
                {"value": "direct", "label": "Tell me straight", "reaction": "Clear and honest. Now we know exactly what to fix before the fair."},
                {"value": "gentle", "label": "Kindly, with a smile", "reaction": "Kind words and a little flower. Aww. Now we can fix it, feeling good."},
                {"value": "written", "label": "Write it down for me", "reaction": "A neat note on a lily pad. We can read it whenever we're ready."},
                {"value": "private", "label": "Just between us", "reaction": "Just between friends. Quietly fixed, and nobody had to know."},
            ],
        },
        {
            "id": "rainstorm",
            "title": "The Rainstorm",
            "field": "cool_down",
            "line": "Step four: a storm rolls in while we finish the app! Wind, rain, everyone talking at once! When things get too much, what should happen?",
            "choices": [
                {"value": "break_signal", "label": "I raise my flag for a break", "reaction": "Up goes the flag, and the whole pond pauses. The storm passes, and the app is finished."},
                {"value": "step_away", "label": "I tuck into my shell for a bit", "reaction": "Shell time! The storm passes while you rest, and you come out ready to finish the app."},
                {"value": "switch_to_text", "label": "Switch to writing", "reaction": "Everyone switches to message bottles. Quiet again, and the app gets finished."},
                {"value": "none", "label": "I'm good, I can ride it out", "reaction": "You surf the waves like a pro. The storm passes, and the app is finished."},
            ],
        },
        {
            "id": "pond_fair",
            "title": "The Pond Fair",
            "field": "presentation_role",
            "line": "The Pond Fair is starting, and the app is ready! Everyone is here to see it. How do you want to be part of the big demo?",
            "choices": [
                {"value": "lead", "label": "Lead the presentation", "reaction": "Spotlight on you! The pond cheers."},
                {"value": "short_part", "label": "A short part", "reaction": "A quick, shining moment. Perfect."},
                {"value": "behind_scenes", "label": "Run the demo behind the scenes", "reaction": "You pull the lever and the demo runs flawlessly. Backstage hero!"},
            ],
        },
    ],
    "finale": "The app was a hit, and the pond is calm. You're an official Pond Keeper. Take a bow... slowly.",
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
        labels = [c["label"] for p in picked for c in scene["choices"] if c["value"] == p]
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
