import asyncpg
from os import environ as env

from connection import ME

# kind -> (likes table, its id column, liked table, that table's owner column)
KINDS = {
    "post": ("post_likes", "post_id", "posts", "author_id"),
    "project": ("project_likes", "project_id", "projects", "owner_id"),
}


def like_columns(kind, alias="p"):
    """SELECT columns giving like_count and liked (by the logged-in user, $1) for the row `alias`.
    Add them to any query that lists posts or projects, then pass the row to like_json."""
    table, column, _, _ = KINDS[kind]
    return f"""
        (SELECT count(*) FROM {table} l WHERE l.{column} = {alias}.id) AS like_count,
        EXISTS (SELECT 1 FROM {table} l WHERE l.{column} = {alias}.id AND l.user_id = {ME}) AS liked
    """


def like_json(row):
    return {"count": row["like_count"], "liked": row["liked"]}


async def set_like(auth0_sub, kind, item_id, liked):
    """Like (liked=True) or unlike a post or project. Liking twice or unliking something you
    hadn't liked changes nothing. Returns {count, liked}, or None if it doesn't exist or its
    author/owner and the logged-in user have blocked each other (either way)."""
    table, column, items, owner = KINDS[kind]
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        visible = await conn.fetchval(
            f"""
            SELECT EXISTS (
                SELECT 1 FROM {items} p
                WHERE p.id = $2 AND NOT EXISTS (
                    SELECT 1 FROM blocks b
                    WHERE (b.blocker_id = p.{owner} AND b.blocked_id = {ME})
                       OR (b.blocker_id = {ME} AND b.blocked_id = p.{owner})
                )
            )
            """,
            auth0_sub, item_id,
        )
        if not visible:
            return None

        if liked:
            await conn.execute(
                f"INSERT INTO {table} ({column}, user_id) VALUES ($2, {ME}) ON CONFLICT DO NOTHING",
                auth0_sub, item_id,
            )
        else:
            await conn.execute(f"DELETE FROM {table} WHERE {column} = $2 AND user_id = {ME}", auth0_sub, item_id)

        row = await conn.fetchrow(f"SELECT {like_columns(kind)} FROM {items} p WHERE p.id = $2", auth0_sub, item_id)
    finally:
        await conn.close()

    return like_json(row)
