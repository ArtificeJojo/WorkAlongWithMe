"""Tests for the quests: pages, saving to the database, unlocking, privacy and validation.

Run from the flask folder with a TEST database (never the real one):
    set TEST_DATABASE_URL=postgres://...    (Windows)   export TEST_DATABASE_URL=...  (Mac/Linux)
    python -m pytest test_quests.py -q
Login is faked, so Auth0 isn't needed. Test users are named "__test__" and deleted afterwards.
"""

import asyncio
import builtins
import json
import os
import re

import asyncpg
import pytest

TEST_DB = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="set TEST_DATABASE_URL to a test database")

if TEST_DB:
    os.environ["DATABASE_URL"] = TEST_DB

import app as app_module  # noqa: E402
import quests  # noqa: E402

# The app opens pages with Windows paths ("..\\src\\x.html"); make that work on any OS.
_real_open = builtins.open


def _open(path, *args, **kwargs):
    if isinstance(path, str) and "\\" in path:
        path = os.path.join(os.path.dirname(__file__), *path.split("\\"))
    return _real_open(path, *args, **kwargs)


SUB = "test|quest-hero"


class FakeAuth0:
    def __init__(self, sub):
        self.sub = sub

    async def get_user(self, **_):
        return {"sub": self.sub} if self.sub else None


def run(coro):
    return asyncio.run(coro)


async def _sql(query, *args, fetch=False):
    conn = await asyncpg.connect(TEST_DB)
    try:
        return await (conn.fetch(query, *args) if fetch else conn.execute(query, *args))
    finally:
        await conn.close()


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(builtins, "open", _open)
    run(_sql("DELETE FROM users WHERE display_name = '__test__'"))
    run(_sql(
        "INSERT INTO users (display_name, auth0_sub, organization, about_you_completed) VALUES ('__test__', $1, 'UF', TRUE)",
        SUB,
    ))
    monkeypatch.setattr(app_module, "auth0", lambda: FakeAuth0(SUB))
    app_module.app.config["TESTING"] = True
    yield app_module.app.test_client()
    run(_sql("DELETE FROM users WHERE display_name = '__test__'"))


GATOR_ANSWERS = {
    "roles": ["builder", "designer"],
    "task_format": "cards",
    "task_size": "bite_sized",
    "pacing": "checkins",
    "info_styles": ["visual"],
}
TURTLE_ANSWERS = {
    "communication": "text",
    "processing_time": "take_time",
    "feedback_style": "gentle",
    "cool_down": "switch_to_text",
    "presentation_role": "behind_scenes",
}


def finish(client, quest_id, answers, visibility=None):
    return client.post(f"/quest/{quest_id}/finish", json={"answers": answers, "visibility": visibility or {}})


# ------------------------------------------------------------------ definitions (no database)

def test_every_choice_is_a_value_the_database_accepts():
    for quest in quests.QUESTS.values():
        for scene in quest["scenes"]:
            values = [c["value"] for c in scene["choices"]]
            assert sorted(values) == sorted(quests.ALLOWED[scene["field"]]), scene["id"]
            for c in scene["choices"]:
                assert c["label"] and c["reaction"]


def test_quests_cover_all_fields_once():
    fields = [s["field"] for q in quests.QUESTS.values() for s in q["scenes"]]
    assert sorted(fields) == sorted(quests.FIELDS)


def test_no_losing_and_no_disability_words_in_the_story():
    text = json.dumps(quests.QUESTS).lower()
    for word in ["adhd", "autis", "deaf", "disab", "stutter", "anxiety", "dyslex", "game over", "you lose", "failed"]:
        assert word not in text, word


def test_script_json_cannot_break_out_of_a_script_tag():
    assert "</script>" not in quests.to_script_json({"x": "</script><script>alert(1)</script>"})


# ------------------------------------------------------------------ pages and saving

def test_about_you_goes_straight_to_home(client):
    # About you no longer needs a track, and there's no setup quiz after it: quests are optional from /home
    r = client.post("/aboutyou", data={"username": "__test__", "organization": "UF"})
    assert r.status_code == 302 and r.headers["Location"].endswith("/home")
    assert client.get("/home").status_code == 200
    assert client.get("/quest").headers["Location"].endswith("/quest/gators")


def test_gators_page_renders_with_its_story(client):
    r = client.get("/quest/gators")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "/js/pixel.js" in html
    data = json.loads(re.search(r"const DATA = (\{.*?\});\n", html).group(1))
    assert data["quests"]["gators"]["guide"] == "Chomp"


def test_turtle_is_locked_until_gators_is_done(client):
    r = client.get("/quest/turtle")
    assert r.status_code == 302 and r.headers["Location"].endswith("/quest/gators")
    r = finish(client, "turtle", TURTLE_ANSWERS)
    assert r.status_code == 400


def test_full_journey_saves_both_quests_to_tiger_data(client):
    r = finish(client, "gators", GATOR_ANSWERS, {"pacing": "after_match"})
    assert r.status_code == 200, r.get_json()
    body = r.get_json()
    assert body["progress"]["completed"] == ["gators"]
    assert "turtle" in body["progress"]["unlocked"]
    assert body["summary"][0]["title"] == "Choose Your Powers"

    assert client.get("/quest/turtle").status_code == 200
    r = finish(client, "turtle", TURTLE_ANSWERS, {"cool_down": "private"})
    assert r.status_code == 200
    progress = r.get_json()["progress"]
    assert sorted(progress["completed"]) == ["gators", "turtle"]
    assert progress["answers"] == {**GATOR_ANSWERS, **TURTLE_ANSWERS}
    assert progress["visibility"] == {"pacing": "after_match", "cool_down": "private"}

    rows = run(_sql(
        "SELECT p.* FROM profiles p JOIN users u ON u.id = p.user_id WHERE u.auth0_sub = $1", SUB, fetch=True,
    ))
    assert rows[0]["communication"] == "text" and list(rows[0]["roles"]) == ["builder", "designer"]
    # Both done: /quest now points to the Tavern
    assert client.get("/quest").headers["Location"].endswith("/tavern")


def test_replaying_keeps_one_badge_and_updates_answers(client):
    finish(client, "gators", GATOR_ANSWERS)
    r = finish(client, "gators", {**GATOR_ANSWERS, "task_size": "large"})
    assert r.get_json()["progress"]["completed"] == ["gators"]
    assert r.get_json()["progress"]["answers"]["task_size"] == "large"


def test_skipped_scenes_still_finish_the_quest(client):
    r = finish(client, "gators", {"roles": [], "task_format": None, "task_size": None, "pacing": None, "info_styles": []})
    assert r.status_code == 200 and r.get_json()["progress"]["completed"] == ["gators"]


@pytest.mark.parametrize("answers", [
    {"task_size": "medium"},
    {"roles": ["builder", "designer", "leader"]},
    {"roles": "builder"},
    {"info_styles": ["visual", "visual"]},
])
def test_invalid_answers_are_rejected(client, answers):
    r = finish(client, "gators", answers)
    assert r.status_code == 400 and r.get_json()["error"]


def test_a_quest_cannot_save_another_quests_questions(client):
    finish(client, "gators", {**GATOR_ANSWERS, "communication": "voice"})
    progress = client.get("/quest-progress").get_json()
    assert progress["answers"]["communication"] is None


def test_bad_privacy_values_are_ignored(client):
    r = finish(client, "gators", GATOR_ANSWERS, {"pacing": "everyone", "hacker": "public"})
    assert r.get_json()["progress"]["visibility"] == {}


def test_unknown_quest_and_logged_out(client, monkeypatch):
    assert client.get("/quest/dragons").status_code == 404
    monkeypatch.setattr(app_module, "auth0", lambda: FakeAuth0(None))
    assert finish(client, "gators", GATOR_ANSWERS).status_code == 401
    assert client.get("/quest/gators").status_code == 302


def test_pixel_script_is_served(client):
    r = client.get("/js/pixel.js")
    assert r.status_code == 200 and b"window.Pixel" in r.data


def test_home_shows_quest_cards_and_tavern_after_both(client):
    finish(client, "gators", GATOR_ANSWERS)
    html = client.get("/home").get_data(as_text=True)
    assert "Swamp Launcher badge earned" in html and "Start quest" in html
    assert "Enter the Tavern" not in html
    finish(client, "turtle", TURTLE_ANSWERS)
    html = client.get("/home").get_data(as_text=True)
    assert "Swamp Launcher badge earned" in html and "Pond Keeper badge earned" in html
    assert "Enter the Tavern" in html
