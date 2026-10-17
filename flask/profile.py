import asyncpg
from os import environ as env
from pathlib import Path
from uuid import uuid4

from flask import send_from_directory

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PICTURE = ROOT / "assets" / "donkey.jpg"
UPLOAD_DIR = ROOT / "uploads" / "profile_pictures"
# Only image types, so an upload can never be served back as HTML or script
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


async def send_profile_picture(auth0_sub):
    """Respond with the user's uploaded picture, or the default donkey if they haven't uploaded one."""
    return await send_picture("SELECT profile_picture FROM users WHERE auth0_sub = $1", auth0_sub)


async def send_picture(query, key):
    """Respond with the uploaded picture whose filename query returns for key, or the default donkey."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        filename = await conn.fetchval(query, key)
    finally:
        await conn.close()

    if filename and (UPLOAD_DIR / filename).is_file():
        return send_from_directory(UPLOAD_DIR, filename)
    return send_from_directory(DEFAULT_PICTURE.parent, DEFAULT_PICTURE.name)


async def replace_profile_picture(auth0_sub, file):
    """Save an uploaded picture as the user's new one and delete their previous upload.
    Raises ValueError if the file isn't an allowed image type."""
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Profile picture must be a .jpg, .jpeg, .png, .gif or .webp file")

    # Random name: users never pick server-side filenames, and the URL changes so browsers don't show a stale copy
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = uuid4().hex + extension
    file.save(UPLOAD_DIR / filename)

    try:
        await _set_profile_picture(auth0_sub, filename)
    except Exception:
        (UPLOAD_DIR / filename).unlink(missing_ok=True)
        raise


async def reset_profile_picture(auth0_sub):
    """Go back to the default donkey and delete the user's uploaded picture, if any."""
    await _set_profile_picture(auth0_sub, None)


async def has_custom_profile_picture(auth0_sub):
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        filename = await conn.fetchval(
            "SELECT profile_picture FROM users WHERE auth0_sub = $1", auth0_sub,
        )
    finally:
        await conn.close()

    return bool(filename and (UPLOAD_DIR / filename).is_file())


async def _set_profile_picture(auth0_sub, filename):
    """Point the user at a new uploaded file (None = default) and delete the file they had before."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        async with conn.transaction():
            old_filename = await conn.fetchval(
                "SELECT profile_picture FROM users WHERE auth0_sub = $1 FOR UPDATE", auth0_sub,
            )
            await conn.execute(
                "UPDATE users SET profile_picture = $1 WHERE auth0_sub = $2", filename, auth0_sub,
            )
    finally:
        await conn.close()

    # The default picture lives in assets/ and is never stored here, so it can't be deleted
    if old_filename:
        (UPLOAD_DIR / old_filename).unlink(missing_ok=True)
