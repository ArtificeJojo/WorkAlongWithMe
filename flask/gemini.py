import asyncpg
from functools import lru_cache
from os import environ as env

from google import genai

from connection import ME

# Instructions given to Gemini for each /aboutyou track (users.track). Fill these in later.
GATOR_PROMPT = """
From now, you are Gator, you are an alligator, 
"""
TURTLE_PROMPT = ""

TRACK_PROMPTS = {
    "gators": GATOR_PROMPT,
    "turtle": TURTLE_PROMPT,
}


@lru_cache(maxsize=1)
def init_gemini():
    """The Gemini client, using GEMINI_KEY from .env. Created once and reused."""
    api_key = env.get("GEMINI_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_KEY is missing from .env")
    return genai.Client(api_key=api_key)


def prompt_for_track(track):
    """The prompt for a track ('gators' or 'turtle'). Raises ValueError for anything else."""
    if track not in TRACK_PROMPTS:
        raise ValueError(f"Unknown track: {track!r}")
    return TRACK_PROMPTS[track]


async def prompt_for_user(auth0_sub):
    """The prompt for the logged-in user's track. Raises ValueError if they haven't picked one."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        track = await conn.fetchval(f"SELECT track FROM users WHERE id = {ME}", auth0_sub)
    finally:
        await conn.close()

    return prompt_for_track(track)
