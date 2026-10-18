"""Technical skills from /aboutyou. Users can type any skill; skills.txt only feeds the suggestions."""
import profile

SKILLS_FILE = profile.ROOT / "skills.txt"
MAX_SKILLS = 5
MAX_LENGTH = 50


def suggestions():
    """The skills in skills.txt, one per line, without blanks or repeats. Read on every call so edits show up right away."""
    try:
        lines = SKILLS_FILE.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    seen, skills = set(), []
    for line in lines:
        skill = line.strip()
        if skill and skill.lower() not in seen:
            seen.add(skill.lower())
            skills.append(skill)
    return skills


def clean(submitted):
    """Trims, drops blanks and repeats (ignoring case), and keeps the first MAX_SKILLS.
    A skill matching one in skills.txt takes that spelling, e.g. "python" -> "Python"."""
    listed = {skill.lower(): skill for skill in suggestions()}
    seen, skills = set(), []
    for skill in submitted:
        skill = " ".join(skill.split())[:MAX_LENGTH]
        if skill and skill.lower() not in seen:
            seen.add(skill.lower())
            skills.append(listed.get(skill.lower(), skill))
    return skills[:MAX_SKILLS]
