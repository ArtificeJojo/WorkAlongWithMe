import asyncpg
from os import environ as env

import profile

# The logged-in user's users.id, from their Auth0 ID ($1 in every query below that uses it)
ME = "(SELECT id FROM users WHERE auth0_sub = $1)"

# How the logged-in user relates to users row u. Needs the friend_requests join below.
RELATIONSHIP = f"""
    CASE
        WHEN u.id = {ME} THEN 'self'
        WHEN EXISTS (SELECT 1 FROM blocks b WHERE b.blocker_id = {ME} AND b.blocked_id = u.id) THEN 'blocked'
        WHEN fr.status = 'accepted' THEN 'friends'
        WHEN fr.sender_id = {ME} THEN 'request_sent'
        WHEN fr.sender_id = u.id THEN 'request_received'
        ELSE 'none'
    END
"""
FRIEND_REQUEST_JOIN = f"""
    LEFT JOIN friend_requests fr
           ON (fr.sender_id = u.id AND fr.recipient_id = {ME})
           OR (fr.recipient_id = u.id AND fr.sender_id = {ME})
"""
# u has blocked the logged-in user
BLOCKED_BY_U = f"EXISTS (SELECT 1 FROM blocks b WHERE b.blocker_id = u.id AND b.blocked_id = {ME})"


async def send_profile_picture_by_id(auth0_sub, user_id):
    """Respond with any user's profile picture by their users.id (e.g. search results).
    Users who have blocked each other (either way) get the default picture instead."""
    return await profile.send_picture(
        f"""
        SELECT u.profile_picture FROM users u
        WHERE u.id = $2
          AND NOT {BLOCKED_BY_U}
          AND NOT EXISTS (SELECT 1 FROM blocks b WHERE b.blocker_id = {ME} AND b.blocked_id = u.id)
        """,
        auth0_sub, user_id,
    )


async def search_users(auth0_sub, prefix, limit=4, exclude=()):
    """Users whose username starts with prefix (case-insensitive), alphabetically.
    Only users who finished /aboutyou, since that's where usernames are chosen,
    and never anyone who has blocked the searcher or whose id is in exclude
    (e.g. teammates already added on /project_create).
    Each result says how they relate to the searcher: 'self', 'blocked' (by the searcher),
    'friends', 'request_sent', 'request_received' or 'none'."""
    if not prefix:
        return []

    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        rows = await conn.fetch(
            f"""
            SELECT u.id, u.display_name, {RELATIONSHIP} AS relationship
            FROM users u
            {FRIEND_REQUEST_JOIN}
            WHERE u.about_you_completed AND starts_with(lower(u.display_name), lower($2))
              AND NOT {BLOCKED_BY_U}
              AND u.id <> ALL($4::uuid[])
            ORDER BY lower(u.display_name), u.id
            LIMIT $3
            """,
            auth0_sub, prefix, limit, list(exclude),
        )
    finally:
        await conn.close()

    return [{**_user_json(row), "relationship": row["relationship"]} for row in rows]


async def get_user_profile(auth0_sub, user_id):
    """Another user's profile as the logged-in user sees it: id, username, picture and relationship.
    None if they don't exist, haven't finished /aboutyou, or either of you has blocked the other
    (indistinguishable on purpose, so a block isn't revealed)."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        row = await conn.fetchrow(
            f"""
            SELECT u.id, u.display_name, {RELATIONSHIP} AS relationship
            FROM users u
            {FRIEND_REQUEST_JOIN}
            WHERE u.id = $2 AND u.about_you_completed AND NOT {BLOCKED_BY_U}
            """,
            auth0_sub, user_id,
        )
    finally:
        await conn.close()

    if not row or row["relationship"] == "blocked":
        return None
    return {**_user_json(row), "relationship": row["relationship"]}


async def send_friend_request(auth0_sub, user_id):
    """Ask user_id to be friends. If they had already asked us, that counts as accepting.
    Returns the new relationship ('request_sent' or 'friends').
    Raises ValueError for yourself, a user who doesn't exist / hasn't finished /aboutyou,
    or when either of you has blocked the other (same message, so a block isn't revealed)."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        async with conn.transaction():
            me = await conn.fetchval(f"SELECT {ME}", auth0_sub)
            target = await conn.fetchval(
                "SELECT id FROM users WHERE id = $1 AND about_you_completed", user_id,
            )
            if not target or target == me:
                raise ValueError("You can't send a friend request to that user")

            await _lock_pair(conn, me, target)
            blocked = await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM blocks WHERE (blocker_id = $1 AND blocked_id = $2) "
                "OR (blocker_id = $2 AND blocked_id = $1))",
                me, target,
            )
            if blocked:
                raise ValueError("You can't send a friend request to that user")

            accepted = await conn.fetchval(
                "UPDATE friend_requests SET status = 'accepted', sender_seen = FALSE, responded_at = now() "
                "WHERE sender_id = $1 AND recipient_id = $2 AND status = 'pending' RETURNING TRUE",
                target, me,
            )
            if not accepted:
                # Does nothing if a request or friendship already exists in either direction
                await conn.execute(
                    "INSERT INTO friend_requests (sender_id, recipient_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                    me, target,
                )

            status = await conn.fetchval(
                "SELECT CASE WHEN status = 'accepted' THEN 'friends' ELSE 'request_sent' END "
                "FROM friend_requests WHERE (sender_id = $1 AND recipient_id = $2) OR (sender_id = $2 AND recipient_id = $1)",
                me, target,
            )
    finally:
        await conn.close()

    return status


async def respond_to_friend_request(auth0_sub, sender_id, accept):
    """Accept or reject a pending request sent to the logged-in user.
    Rejecting deletes it. Returns False if there was no such pending request."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        if accept:
            result = await conn.execute(
                "UPDATE friend_requests SET status = 'accepted', sender_seen = FALSE, responded_at = now() "
                f"WHERE sender_id = $2 AND recipient_id = {ME} AND status = 'pending'",
                auth0_sub, sender_id,
            )
        else:
            result = await conn.execute(
                f"DELETE FROM friend_requests WHERE sender_id = $2 AND recipient_id = {ME} AND status = 'pending'",
                auth0_sub, sender_id,
            )
    finally:
        await conn.close()

    return not result.endswith(" 0")


async def remove_friend(auth0_sub, user_id):
    """Unfriend user_id, whichever of you sent the original request. The other user isn't told;
    they just stop seeing you in their list. Returns False if you weren't friends."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        result = await conn.execute(
            f"""
            DELETE FROM friend_requests
            WHERE status = 'accepted'
              AND ((sender_id = {ME} AND recipient_id = $2) OR (sender_id = $2 AND recipient_id = {ME}))
            """,
            auth0_sub, user_id,
        )
    finally:
        await conn.close()

    return not result.endswith(" 0")


async def block_user(auth0_sub, user_id):
    """Block user_id: unfriend them and delete any pending friend or collaborator request either way.
    Raises ValueError for yourself or a user who doesn't exist."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        async with conn.transaction():
            me = await conn.fetchval(f"SELECT {ME}", auth0_sub)
            target = await conn.fetchval("SELECT id FROM users WHERE id = $1", user_id)
            if not target or target == me:
                raise ValueError("You can't block that user")

            await _lock_pair(conn, me, target)
            await conn.execute(
                "INSERT INTO blocks (blocker_id, blocked_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                me, target,
            )
            await conn.execute(
                "DELETE FROM friend_requests WHERE (sender_id = $1 AND recipient_id = $2) "
                "OR (sender_id = $2 AND recipient_id = $1)",
                me, target,
            )
            # Pending requests to collaborate on each other's projects too, so they stop
            # taking up one of the project's 5 request spots
            await conn.execute(
                "DELETE FROM collaborator_requests r USING projects p "
                "WHERE p.id = r.project_id AND r.status = 'pending' "
                "AND ((r.user_id = $1 AND p.owner_id = $2) OR (r.user_id = $2 AND p.owner_id = $1))",
                me, target,
            )
    finally:
        await conn.close()


async def unblock_user(auth0_sub, user_id):
    """Returns False if the user hadn't blocked user_id. Unblocking doesn't restore any friendship."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        result = await conn.execute(
            f"DELETE FROM blocks WHERE blocker_id = {ME} AND blocked_id = $2", auth0_sub, user_id,
        )
    finally:
        await conn.close()

    return not result.endswith(" 0")


async def _lock_pair(conn, a, b):
    """Lock both users' rows (in a fixed order, so it can't deadlock) for the rest of the transaction.
    Blocking and sending a request between the same two people then can't interleave and leave
    a request behind a block."""
    await conn.execute(
        "SELECT id FROM users WHERE id IN ($1, $2) ORDER BY id FOR UPDATE", a, b,
    )


async def get_connections(auth0_sub):
    """Everything connections.html shows: friends, incoming pending requests, blocked users, and
    whether any of the user's sent requests were accepted since they last opened the Friends tab."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        friends = await conn.fetch(
            f"""
            SELECT u.id, u.display_name
            FROM friend_requests fr
            JOIN users u ON u.id = CASE WHEN fr.sender_id = {ME} THEN fr.recipient_id ELSE fr.sender_id END
            WHERE fr.status = 'accepted' AND {ME} IN (fr.sender_id, fr.recipient_id)
            ORDER BY lower(u.display_name), u.id
            """,
            auth0_sub,
        )
        requests = await conn.fetch(
            f"""
            SELECT u.id, u.display_name
            FROM friend_requests fr
            JOIN users u ON u.id = fr.sender_id
            WHERE fr.status = 'pending' AND fr.recipient_id = {ME}
            ORDER BY fr.created_at
            """,
            auth0_sub,
        )
        blocked = await conn.fetch(
            f"""
            SELECT u.id, u.display_name
            FROM blocks b
            JOIN users u ON u.id = b.blocked_id
            WHERE b.blocker_id = {ME}
            ORDER BY lower(u.display_name), u.id
            """,
            auth0_sub,
        )
        new_friends = await conn.fetchval(
            f"SELECT EXISTS (SELECT 1 FROM friend_requests WHERE sender_id = {ME} AND status = 'accepted' AND NOT sender_seen)",
            auth0_sub,
        )
    finally:
        await conn.close()

    return {
        "friends": [_user_json(row) for row in friends],
        "requests": [_user_json(row) for row in requests],
        "blocked": [_user_json(row) for row in blocked],
        "new_friends": new_friends,
    }


async def mark_new_friends_seen(auth0_sub):
    """The user opened their Friends tab: stop highlighting it."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        await conn.execute(
            f"UPDATE friend_requests SET sender_seen = TRUE WHERE sender_id = {ME} AND NOT sender_seen",
            auth0_sub,
        )
    finally:
        await conn.close()


def _user_json(row):
    return {"id": str(row["id"]), "username": row["display_name"], "picture": f"/users/{row['id']}/picture"}
