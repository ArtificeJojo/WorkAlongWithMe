import asyncpg
from os import environ as env

import profile


async def send_profile_picture_by_id(user_id):
    """Respond with any user's profile picture by their users.id (e.g. search results)."""
    return await profile.send_picture("SELECT profile_picture FROM users WHERE id = $1", user_id)


async def search_users(prefix, limit=4):
    """Users whose username starts with prefix (case-insensitive), alphabetically.
    Only users who finished /aboutyou, since that's where usernames are chosen."""
    if not prefix:
        return []

    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        rows = await conn.fetch(
            "SELECT id, display_name FROM users "
            "WHERE about_you_completed AND starts_with(lower(display_name), lower($1)) "
            "ORDER BY lower(display_name), id LIMIT $2",
            prefix, limit,
        )
    finally:
        await conn.close()

    return [
        {"id": str(row["id"]), "username": row["display_name"], "picture": f"/users/{row['id']}/picture"}
        for row in rows
    ]
