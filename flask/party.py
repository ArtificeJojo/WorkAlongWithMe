"""Parties (groups) and the Party Pact: the team's agreements, written from everyone's quest answers.

Gemini writes the pact when GEMINI_API_KEY is set; otherwise (or if Gemini fails) a rule-based
pact is written instead, so the demo never breaks. Only answers a student did NOT mark
"Only me" are ever used; no disability or diagnosis information exists in the data at all.
"""

import json
import re
from collections import Counter
from os import environ as env
from uuid import UUID

import asyncpg

from matching import get_all_profiles, label, visibility_of
from quests import FIELDS

MAX_PARTY = 4

# Emoji and pictographic symbols. The quest pages don't use emoji, so they're stripped from anything
# Gemini writes (and from pacts saved before that).
EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2190-\u21FF\u25A0-\u25FF\u2300-\u23FF\uFE0F\u200D]"
)


def strip_emoji(text):
    return re.sub(r"\s{2,}", " ", EMOJI.sub("", text)).strip()
DEFAULT_MODEL = "gemini-3.6-flash"


class PartyError(Exception):
    pass


# ------------------------------------------------------------------ what each member is happy to share

PLAIN = {
    "communication": {"text": "prefers the group chat over calls", "voice": "likes quick voice calls",
                      "in_person": "likes meeting in person", "mix": "is happy with any way of talking"},
    "processing_time": {"instant": "likes quick back-and-forth", "take_time": "needs time to think and finish speaking"},
    "feedback_style": {"direct": "wants feedback straight", "gentle": "wants feedback given kindly",
                       "written": "wants feedback in writing", "private": "wants feedback one-on-one"},
    "cool_down": {"break_signal": "may raise a flag for a short break", "step_away": "may step away quietly for a bit",
                  "switch_to_text": "may switch to writing when things get loud", "none": "is fine riding out busy moments"},
    "presentation_role": {"lead": "wants to lead the presentation", "short_part": "wants a short speaking part",
                          "behind_scenes": "wants to run the demo behind the scenes"},
    "task_format": {"list": "plans with one big list", "cards": "plans with movable task cards", "checklist": "plans with a checklist"},
    "task_size": {"large": "likes big chunks of work", "bite_sized": "likes tasks broken into small pieces"},
    "pacing": {"single_deadline": "works toward one final deadline", "checkins": "likes small check-ins along the way",
               "flexible": "likes flexible timing"},
}


def shareable(p):
    """A member's answers that may go into the pact (everything except 'Only me')."""
    return {f: p.get(f) for f in FIELDS if visibility_of(p, f) != "private" and p.get(f) not in (None, [])}


def describe(p, limit=None):
    s = shareable(p)
    bits = [PLAIN[f][s[f]] for f in PLAIN if f in s]
    if limit:
        return "; ".join(bits[:limit]) or "shared nothing yet"
    if s.get("info_styles"):
        bits.append(f"learns best from {', '.join(label(v) for v in s['info_styles'])} instructions")
    if s.get("roles"):
        bits.append(f"has {' and '.join(label(r) for r in s['roles'])} powers")
    return f"{p['display_name']}: " + ("; ".join(bits) if bits else "shared nothing yet")


def chips(public):
    """Short labels for a match's hero card, from their PUBLIC answers only."""
    out = [f"{label(r).capitalize()} power" for r in public.get("roles") or []]
    for f in ("communication", "pacing", "task_size", "presentation_role"):
        v = public.get(f)
        if v:
            out.append(PLAIN[f][v])
    return out


# ------------------------------------------------------------------ the pact

def fallback_pact(members):
    """Rule-based pact used when Gemini is unavailable. Every rule is phrased for the whole team."""
    s = [shareable(m) for m in members]
    pick = lambda f: [x[f] for x in s if f in x]
    rules = []

    comm = Counter(pick("communication"))
    if comm:
        top = comm.most_common(1)[0][0]
        rules.append({
            "text": "Make decisions in the group chat, so everyone can keep up and look back later.",
            "voice": "Use short voice calls for decisions, then post a written summary in the chat.",
            "in_person": "Meet in person for big decisions, and post a written summary for anyone who missed it.",
            "mix": "Mix chat, calls and meetups, and always post decisions in writing afterward.",
        }[top])
    if "take_time" in pick("processing_time"):
        rules.append("Give everyone time to think and to finish speaking. Nobody finishes anyone else's sentences.")
    # Who presents is decided by each person's own choice, never by assumptions.
    leads = [m["display_name"] for m, x in zip(members, s) if x.get("presentation_role") == "lead"]
    backstage = [m["display_name"] for m, x in zip(members, s) if x.get("presentation_role") == "behind_scenes"]
    if leads or backstage:
        parts = []
        if leads:
            parts.append(f"{' and '.join(leads)} {'leads' if len(leads) == 1 else 'lead'} the presentation")
        if backstage:
            parts.append(f"{' and '.join(backstage)} {'runs' if len(backstage) == 1 else 'run'} the demo behind the scenes")
        sentence = "; ".join(parts)
        rules.append(sentence[0].upper() + sentence[1:] + ". Everyone else picks the part that suits them.")
    if any(v != "none" for v in pick("cool_down")):
        rules.append("Anyone can call a timeout (a break flag, stepping away, or switching to writing), no questions asked.")
    if "bite_sized" in pick("task_size") or "cards" in pick("task_format"):
        rules.append("Break big tasks into small pieces on a shared board, with one owner per piece.")
    pacing = Counter(pick("pacing"))
    if pacing:
        rules.append({
            "checkins": "Do a quick check-in at agreed times, instead of surprise pings.",
            "single_deadline": "Agree on one clear final deadline and work backward from it.",
            "flexible": "Keep timing flexible, but say early if something might slip.",
        }[pacing.most_common(1)[0][0]])
    if any(v in ("gentle", "written", "private") for v in pick("feedback_style")):
        rules.append("Give feedback kindly and in writing, and share tough notes one-on-one.")
    if not rules:
        rules.append("Check in with each other about how you like to work, and update this pact together.")
    return rules[:6]


def _gemini_client():
    key = env.get("GEMINI_KEY") or env.get("GEMINI_API_KEY")  # GEMINI_KEY is the name in .env.example
    if not key:
        return None
    try:
        from google import genai
    except ImportError:
        return None
    return genai.Client(api_key=key)


def _ask_gemini_json(prompt):
    client = _gemini_client()
    if not client:
        return None
    response = client.models.generate_content(
        model=env.get("GEMINI_MODEL", DEFAULT_MODEL),
        contents=prompt,
        config={"response_mime_type": "application/json", "temperature": 0.6},
    )
    return json.loads(response.text)


def gemini_pact(members):
    prompt = (
        "You write a short, warm 'Party Pact' for a student project team: 4 to 6 team agreements that help "
        "everyone work the way they do best and feel included.\n"
        "Rules: phrase each agreement for the whole team (\"We...\"), under 25 words, concrete and kind. "
        "You may name people only for roles they chose (like who presents). Never guess or mention health, "
        "disability or diagnoses. Use only the information below. Don't use emoji.\n\n"
        "Team members and how they like to work:\n"
        + "\n".join(f"- {describe(m)}" for m in members)
        + '\n\nReturn JSON: {"rules": ["...", "..."]}'
    )
    data = _ask_gemini_json(prompt)
    rules = data.get("rules") if isinstance(data, dict) else None
    if not isinstance(rules, list):
        return None
    rules = [strip_emoji(r) for r in rules if isinstance(r, str)]
    rules = [r for r in rules if 0 < len(r) <= 220]
    return rules[:6] if len(rules) >= 3 else None


def write_pact(members):
    """Returns {"rules": [...], "source": "gemini" | "fallback"}."""
    try:
        rules = gemini_pact(members)
        if rules:
            return {"rules": rules, "source": "gemini"}
    except Exception:
        pass
    return {"rules": fallback_pact(members), "source": "fallback"}


def explain_matches(me_name, matches):
    """Adds a friendly one-line 'why' to each match. Uses only reasons that are already public."""
    distinctive = lambda r: 0 if r.startswith("They bring") else 1 if "present" in r else 2
    for m in matches:
        reasons = sorted(m["reasons"], key=distinctive)  # lead with what makes each match different
        m["why"] = (". ".join(reasons[:2]) + ".") if reasons else "You could balance each other out."
    if not matches or not any(m["reasons"] for m in matches):
        return matches
    try:
        prompt = (
            f"Write one friendly sentence (under 30 words) per teammate match for {me_name}, saying why they'd work "
            "well together. Use ONLY the reasons given; never guess anything else. Don't use emoji.\n"
            + "\n".join(f'{i}. {m["hero"]["display_name"]}: {"; ".join(m["reasons"])}' for i, m in enumerate(matches))
            + '\nReturn JSON: {"sentences": ["...", ...]} in the same order.'
        )
        data = _ask_gemini_json(prompt)
        sentences = data.get("sentences") if isinstance(data, dict) else None
        if isinstance(sentences, list) and len(sentences) == len(matches):
            for m, s in zip(matches, sentences):
                if isinstance(s, str) and 0 < len(strip_emoji(s)) <= 240:
                    m["why"] = strip_emoji(s)
    except Exception:
        pass
    return matches


# ------------------------------------------------------------------ database

async def _connect():
    return await asyncpg.connect(env.get("DATABASE_URL"))


async def create_party(auth0_sub, teammate_ids, name):
    """Form a party with up to 3 teammates, write its pact and save it. Returns the group id."""
    name = (name or "").strip()[:60] or "The Unstoppable Party"
    try:
        ids = list(dict.fromkeys(str(UUID(str(i))) for i in teammate_ids))
    except ValueError:
        raise PartyError("Invalid teammate")
    if not 1 <= len(ids) <= MAX_PARTY - 1:
        raise PartyError(f"Pick 1 to {MAX_PARTY - 1} teammates")

    profiles = {p["user_id"]: p for p in await get_all_profiles()}
    me = next((p for p in profiles.values() if p["auth0_sub"] == auth0_sub), None)
    if not me:
        raise PartyError("Finish a quest first")
    if me["user_id"] in ids or any(i not in profiles for i in ids):
        raise PartyError("Invalid teammate")
    members = [me] + [profiles[i] for i in ids]

    pact = write_pact(members)
    conn = await _connect()
    try:
        async with conn.transaction():
            group_id = await conn.fetchval(
                "INSERT INTO groups (name, team_guide) VALUES ($1, $2) RETURNING id", name, json.dumps(pact),
            )
            await conn.executemany(
                "INSERT INTO group_members (group_id, user_id) VALUES ($1, $2::uuid)",
                [(group_id, m["user_id"]) for m in members],
            )
    finally:
        await conn.close()
    return str(group_id)


async def get_party(auth0_sub, group_id):
    """The party page data, or None if it doesn't exist or this student isn't in it."""
    conn = await _connect()
    try:
        group = await conn.fetchrow("SELECT id, name, team_guide, created_at FROM groups WHERE id = $1", group_id)
        member_ids = [str(r["user_id"]) for r in await conn.fetch(
            "SELECT user_id FROM group_members WHERE group_id = $1 ORDER BY joined_at", group_id)]
    finally:
        await conn.close()
    if not group:
        return None
    profiles = {p["user_id"]: p for p in await get_all_profiles()}
    me = next((p for p in profiles.values() if p["auth0_sub"] == auth0_sub), None)
    if not me or me["user_id"] not in member_ids:
        return None
    pact = json.loads(group["team_guide"]) if group["team_guide"] else {"rules": [], "source": "fallback"}
    pact["rules"] = [strip_emoji(rule) for rule in pact.get("rules", [])]
    members = []
    for i in member_ids:
        p = profiles.get(i)
        if p:
            # Inside the party, "after we match" answers can be shown; "Only me" never is.
            members.append({"user_id": i, "display_name": p["display_name"], "is_me": i == me["user_id"],
                            "about": describe(p, limit=4)})
    return {"id": str(group["id"]), "name": group["name"], "pact": pact, "members": members}


async def my_parties(auth0_sub):
    conn = await _connect()
    try:
        rows = await conn.fetch(
            "SELECT g.id, g.name FROM groups g JOIN group_members gm ON gm.group_id = g.id "
            "JOIN users u ON u.id = gm.user_id WHERE u.auth0_sub = $1 ORDER BY g.created_at DESC",
            auth0_sub,
        )
    finally:
        await conn.close()
    return [{"id": str(r["id"]), "name": r["name"]} for r in rows]
