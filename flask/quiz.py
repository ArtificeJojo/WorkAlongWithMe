import asyncpg
from os import environ as env

# The "very serious" quiz shown at /quiz after /aboutyou: 4 questions, up to 4 answers each.
# Placeholders for now; replace them with the real questions and answers.
QUESTIONS = [
    {"question": "You are a gator. The swamp is a busy place, so how would you, as a gator, makes notes of the busy swamp", "answers": ["With the SCROLL (notemaxxing)", "With the stick notes (spreadmaxxing)", "With a checklist (listmaxxing)", "I don't need to take notes (high cortisol maxxing)"]},
    {"question": "Question 2", "answers": ["Answer 1", "Answer 2", "Answer 3", "Answer 4"]},
    {"question": "Question 3", "answers": ["Answer 1", "Answer 2", "Answer 3", "Answer 4"]},
    {"question": "Question 4", "answers": ["Answer 1", "Answer 2", "Answer 3", "Answer 4"]},
]

assert all(1 <= len(q["answers"]) <= 4 for q in QUESTIONS), "Each quiz question needs 1 to 4 answers"


def parse_answers(form):
    """The chosen answer index for each question (form fields q0, q1, ...), or None if any is missing or invalid."""
    answers = []
    for i, question in enumerate(QUESTIONS):
        choice = form.get(f"q{i}", "")
        if not choice.isdigit() or int(choice) >= len(question["answers"]):
            return None
        answers.append(int(choice))
    return answers


async def complete_quiz(auth0_sub):
    """Marks the quiz as done, which unlocks /home."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        await conn.execute("UPDATE users SET quiz_completed = TRUE WHERE auth0_sub = $1", auth0_sub)
    finally:
        await conn.close()
