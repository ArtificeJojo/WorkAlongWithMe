"""Tests for the Tavern, parties and the Party Pact. Same setup as test_quests.py (needs TEST_DATABASE_URL).
Gemini is faked, so no API key is needed. Demo heroes come from src/db/seed.sql."""

import asyncio
import os
from pathlib import Path

import pytest

from test_quests import GATOR_ANSWERS, SUB, TEST_DB, TURTLE_ANSWERS, FakeAuth0, _sql, client, finish, run  # noqa: F401

pytestmark = pytest.mark.skipif(not TEST_DB, reason="set TEST_DATABASE_URL to a test database")

if TEST_DB:
    import app as app_module
    import party

SEED = Path(__file__).resolve().parent.parent / "src" / "db" / "seed.sql"
MAYA = "00000000-0000-0000-0000-000000000001"  # text, checkins, cards, designer+leader
SAM = "00000000-0000-0000-0000-000000000006"   # made cool_down "Only me" (private)
NIA = "00000000-0000-0000-0000-000000000012"
OTHER_SUB = "test|someone-else"


@pytest.fixture(autouse=True)
def demo_heroes():
    import asyncpg

    async def load():
        conn = await asyncpg.connect(TEST_DB)
        try:
            await conn.execute("DELETE FROM groups")
            await conn.execute(SEED.read_text())
        finally:
            await conn.close()
    run(load())
    yield
    run(_sql("DELETE FROM groups"))


@pytest.fixture()
def no_gemini(monkeypatch):
    monkeypatch.setattr(party, "_ask_gemini_json", lambda prompt: None)


def play_both(client):
    assert finish(client, "gators", GATOR_ANSWERS).status_code == 200
    assert finish(client, "turtle", TURTLE_ANSWERS).status_code == 200


def form(client, teammates, name="The Swamp Squad"):
    return client.post("/tavern/party", json={"teammates": teammates, "name": name})


# ------------------------------------------------------------------ tavern

def test_tavern_needs_the_gators_quest_first(client):
    r = client.get("/tavern")
    assert r.status_code == 302 and r.headers["Location"].endswith("/quiz")


def test_tavern_shows_matches_with_reasons(client, no_gemini):
    play_both(client)
    html = client.get("/tavern").get_data(as_text=True)
    assert "Your matches" in html and "Great matches" in html
    assert "They bring" in html and "skills to the group" in html  # each card leads with what's distinctive
    assert html.count('class="hero"') == 4


def test_tavern_never_shows_private_or_after_match_answers(client, no_gemini):
    play_both(client)
    html = client.get("/tavern").get_data(as_text=True)
    # Sam's cool_down is "Only me", and cool_down is "after we match" for everyone else
    for phrase in party.PLAIN["cool_down"].values():
        assert phrase not in html
    for phrase in party.PLAIN["processing_time"].values():
        assert phrase not in html


def test_gemini_words_the_matches_when_available(client, monkeypatch):
    prompts = []

    def fake(prompt):
        prompts.append(prompt)
        n = prompt.count("\n") - 1
        return {"sentences": [f"Gemini sentence {i}" for i in range(n)]}
    monkeypatch.setattr(party, "_ask_gemini_json", fake)
    play_both(client)
    html = client.get("/tavern").get_data(as_text=True)
    assert "Gemini sentence 0" in html
    # Only public reasons are sent to Gemini
    assert "step_away" not in prompts[0] and "take_time" not in prompts[0]


def test_blocked_users_never_appear(client, no_gemini):
    play_both(client)
    run(_sql(
        "INSERT INTO blocks (blocker_id, blocked_id) SELECT id, $1::uuid FROM users WHERE auth0_sub = $2", MAYA, SUB,
    ))
    html = client.get("/tavern").get_data(as_text=True)
    assert MAYA not in html


# ------------------------------------------------------------------ parties + pact

def test_forming_a_party_writes_a_fallback_pact_without_gemini(client, no_gemini):
    play_both(client)
    r = form(client, [MAYA, NIA])
    assert r.status_code == 201
    html = client.get(f"/party/{r.get_json()['id']}").get_data(as_text=True)
    assert "The Swamp Squad" in html and "Your Party Pact" in html
    assert "Make decisions in the group chat" in html
    assert "Give everyone time to think and to finish speaking" in html
    assert "Nia leads the presentation" in html  # names keep their capital letters
    assert "Written from the answers" in html


def test_gemini_writes_the_pact_and_never_sees_only_me_answers(client, monkeypatch):
    seen = {}

    def fake(prompt):
        seen["prompt"] = prompt
        return {"rules": ["We plan in the group chat.", "We give everyone time to finish.", "We split work into small cards."]}
    monkeypatch.setattr(party, "_ask_gemini_json", fake)
    play_both(client)
    r = form(client, [SAM])
    html = client.get(f"/party/{r.get_json()['id']}").get_data(as_text=True)
    assert "We plan in the group chat." in html and "Written by Gemini" in html
    # Sam marked cool_down "Only me": it must not reach Gemini
    assert "Sam: " in seen["prompt"] and "step away quietly" not in seen["prompt"]
    # "After we match" answers are fine once the party exists
    assert "needs time to think and finish speaking" in seen["prompt"]


def test_broken_gemini_falls_back(client, monkeypatch):
    def boom(prompt):
        raise RuntimeError("quota exceeded")
    monkeypatch.setattr(party, "_ask_gemini_json", boom)
    play_both(client)
    assert client.get("/tavern").status_code == 200
    r = form(client, [MAYA])
    assert r.status_code == 201
    assert "Written from the answers" in client.get(f"/party/{r.get_json()['id']}").get_data(as_text=True)


@pytest.mark.parametrize("teammates", [[], [MAYA, NIA, SAM, "00000000-0000-0000-0000-000000000002"], ["nope"],
                                       ["00000000-0000-0000-0000-999999999999"]])
def test_invalid_parties_are_rejected(client, no_gemini, teammates):
    play_both(client)
    r = form(client, teammates)
    assert r.status_code == 400 and r.get_json()["error"]


def test_cannot_add_yourself(client, no_gemini):
    play_both(client)
    me = client.get("/quest-progress").get_json()["user_id"]
    assert form(client, [me]).status_code == 400


def test_only_members_can_see_a_party(client, monkeypatch, no_gemini):
    play_both(client)
    group_id = form(client, [MAYA]).get_json()["id"]
    run(_sql("INSERT INTO users (display_name, auth0_sub, about_you_completed) VALUES ('__test__', $1, TRUE)", OTHER_SUB))
    monkeypatch.setattr(app_module, "auth0", lambda: FakeAuth0(OTHER_SUB))
    assert client.get(f"/party/{group_id}").status_code == 404


def test_parties_are_listed_in_the_tavern(client, no_gemini):
    play_both(client)
    form(client, [MAYA], name="Gator Gang")
    assert "Gator Gang" in client.get("/tavern").get_data(as_text=True)


def test_fallback_pact_unit():
    members = [
        {"display_name": "Ana", "visibility": {}, "communication": "text", "processing_time": "take_time",
         "cool_down": "break_signal", "presentation_role": "behind_scenes", "task_size": "bite_sized", "pacing": "checkins"},
        {"display_name": "Ben", "visibility": {"cool_down": "private"}, "communication": "text", "presentation_role": "lead",
         "cool_down": "step_away"},
    ]
    rules = party.fallback_pact(members)
    assert 3 <= len(rules) <= 6
    assert any("Ben leads the presentation; Ana runs the demo" in r for r in rules)
