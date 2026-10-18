import asyncpg
import json
from os import environ as env
from pathlib import Path
from uuid import UUID, uuid4

from flask import send_from_directory

import profile
from connection import ME

THUMBNAIL_DIR = profile.ROOT / "uploads" / "project_thumbnails"
MAX_LENGTHS = {"title": 100, "summary": 300, "description": 10000}

# Project p can be viewed by the logged-in user: anyone, unless they and the owner have blocked
# each other (either way) — the same rule as viewing a user's profile
VISIBLE_TO_ME = f"""
    NOT EXISTS (
        SELECT 1 FROM blocks b
        WHERE (b.blocker_id = p.owner_id AND b.blocked_id = {ME})
           OR (b.blocker_id = {ME} AND b.blocked_id = p.owner_id)
    )
"""


# Start of a query that defines `me` (the logged-in user's id, from $1) and `connected`: their
# friends plus their teammates (anyone sharing a project with them as owner or accepted member).
# Used by the home page feeds for projects and posts.
CONNECTIONS_CTE = f"""
    WITH me AS (SELECT {ME} AS id),
    friends AS (
        SELECT CASE WHEN fr.sender_id = me.id THEN fr.recipient_id ELSE fr.sender_id END AS id
        FROM friend_requests fr, me
        WHERE fr.status = 'accepted' AND me.id IN (fr.sender_id, fr.recipient_id)
    ),
    my_projects AS (
        SELECT p.id FROM projects p, me WHERE p.owner_id = me.id
        UNION
        SELECT c.project_id FROM project_contributors c, me WHERE c.user_id = me.id AND c.status = 'accepted'
    ),
    teammates AS (
        SELECT p.owner_id AS id FROM projects p WHERE p.id IN (SELECT id FROM my_projects)
        UNION
        SELECT c.user_id FROM project_contributors c
        WHERE c.status = 'accepted' AND c.project_id IN (SELECT id FROM my_projects)
    ),
    connected AS (SELECT id FROM friends UNION SELECT id FROM teammates)
"""


class ProjectError(ValueError):
    """Bad project submission. missing lists the mandatory fields that were left empty."""

    def __init__(self, message, missing=()):
        super().__init__(message)
        self.missing = list(missing)


async def create_project(auth0_sub, title, summary, description, thumbnail, contributor_ids):
    """Create a project owned by the logged-in user, inviting the teammates they picked.
    thumbnail is an uploaded file or None. Returns the new project's id.
    Raises ProjectError if a mandatory field is empty or anything else is invalid."""
    title, summary, description = _clean_fields(title, summary, description)
    contributors = _parse_user_ids(contributor_ids)
    thumbnail_name = _save_thumbnail(thumbnail)

    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        async with conn.transaction():
            await _check_invitable(conn, auth0_sub, contributors)
            project_id = await conn.fetchval(
                f"""
                INSERT INTO projects (owner_id, title, summary, description, thumbnail)
                VALUES ({ME}, $2, $3, $4, $5) RETURNING id
                """,
                auth0_sub, title, summary, description, thumbnail_name,
            )
            await conn.executemany(
                "INSERT INTO project_contributors (project_id, user_id) VALUES ($1, $2)",
                [(project_id, user_id) for user_id in contributors],
            )
    except Exception:
        if thumbnail_name:
            (THUMBNAIL_DIR / thumbnail_name).unlink(missing_ok=True)
        raise
    finally:
        await conn.close()

    return project_id


async def update_project(auth0_sub, project_id, title, summary, description, thumbnail, remove_thumbnail,
                         contributor_ids):
    """Edit a project the logged-in user owns. Same rules as create_project.
    thumbnail replaces the current one; remove_thumbnail clears it; neither keeps it.
    contributor_ids is the full list of teammates wanted: anyone left out is removed (member or
    pending invite), anyone new is invited (pending), everyone else keeps their status.
    Returns False if the project doesn't exist or isn't theirs."""
    title, summary, description = _clean_fields(title, summary, description)
    contributors = _parse_user_ids(contributor_ids)
    new_thumbnail = _save_thumbnail(thumbnail)

    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        async with conn.transaction():
            old_thumbnail = await conn.fetchrow(
                f"SELECT thumbnail FROM projects WHERE id = $2 AND owner_id = {ME} FOR UPDATE",
                auth0_sub, project_id,
            )
            if old_thumbnail is None:
                if new_thumbnail:
                    (THUMBNAIL_DIR / new_thumbnail).unlink(missing_ok=True)
                return False
            old_thumbnail = old_thumbnail["thumbnail"]

            current = {row["user_id"] for row in await conn.fetch(
                "SELECT user_id FROM project_contributors WHERE project_id = $1", project_id,
            )}
            # Only newly invited people are checked; existing teammates stay unless removed
            invited = [user_id for user_id in contributors if user_id not in current]
            await _check_invitable(conn, auth0_sub, invited)

            thumbnail_name = new_thumbnail or (None if remove_thumbnail else old_thumbnail)
            await conn.execute(
                "UPDATE projects SET title = $2, summary = $3, description = $4, thumbnail = $5 WHERE id = $1",
                project_id, title, summary, description, thumbnail_name,
            )
            await conn.execute(
                "DELETE FROM project_contributors WHERE project_id = $1 AND user_id <> ALL($2::uuid[])",
                project_id, contributors,
            )
            await conn.executemany(
                "INSERT INTO project_contributors (project_id, user_id) VALUES ($1, $2)",
                [(project_id, user_id) for user_id in invited],
            )
    except Exception:
        if new_thumbnail:
            (THUMBNAIL_DIR / new_thumbnail).unlink(missing_ok=True)
        raise
    finally:
        await conn.close()

    # The old file is no longer used once it was replaced or removed
    if old_thumbnail and old_thumbnail != thumbnail_name:
        (THUMBNAIL_DIR / old_thumbnail).unlink(missing_ok=True)
    return True


def _clean_fields(title, summary, description):
    """Trimmed (title, summary, description); description None if empty.
    Raises ProjectError for missing mandatory fields or anything too long."""
    title = (title or "").strip()
    summary = (summary or "").strip()
    description = (description or "").strip() or None

    missing = [field for field, value in (("title", title), ("summary", summary)) if not value]
    if missing:
        raise ProjectError("Some mandatory fields have not been completed", missing)

    for field, value in (("title", title), ("summary", summary), ("description", description)):
        if value and len(value) > MAX_LENGTHS[field]:
            raise ProjectError(f"The {field} is too long ({MAX_LENGTHS[field]} characters max)")

    return title, summary, description


def _parse_user_ids(user_ids):
    try:
        return list({UUID(user_id) for user_id in user_ids})
    except ValueError:
        raise ProjectError("Some teammates can't be added")


def _save_thumbnail(thumbnail):
    """Save an uploaded thumbnail under a random name and return it, or None if there isn't one."""
    if not thumbnail or not thumbnail.filename:
        return None
    extension = Path(thumbnail.filename).suffix.lower()
    if extension not in profile.ALLOWED_EXTENSIONS:
        raise ProjectError("The thumbnail must be a .jpg, .jpeg, .png, .gif or .webp file")
    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
    thumbnail_name = uuid4().hex + extension
    thumbnail.save(THUMBNAIL_DIR / thumbnail_name)
    return thumbnail_name


async def _check_invitable(conn, auth0_sub, user_ids):
    """Teammates must be real users who finished /aboutyou, not you, and not blocked either way."""
    allowed = await conn.fetchval(
        f"""
        SELECT count(*) FROM users u
        WHERE u.id = ANY($2::uuid[]) AND u.about_you_completed AND u.id <> {ME}
          AND NOT EXISTS (
              SELECT 1 FROM blocks b
              WHERE (b.blocker_id = u.id AND b.blocked_id = {ME})
                 OR (b.blocker_id = {ME} AND b.blocked_id = u.id)
          )
        """,
        auth0_sub, user_ids,
    )
    if allowed != len(user_ids):
        raise ProjectError("Some teammates can't be added")


async def has_pending_invites(auth0_sub):
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        return await conn.fetchval(
            f"SELECT EXISTS (SELECT 1 FROM project_contributors WHERE user_id = {ME} AND status = 'pending')",
            auth0_sub,
        )
    finally:
        await conn.close()


async def get_invites(auth0_sub):
    """The logged-in user's pending project invites, newest first: project title and thumbnail,
    who created it, and who has already accepted."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        invites = await conn.fetch(
            f"""
            SELECT p.id, p.title, p.thumbnail IS NOT NULL AS has_thumbnail,
                   o.id AS owner_id, o.display_name AS owner_name
            FROM project_contributors c
            JOIN projects p ON p.id = c.project_id
            JOIN users o ON o.id = p.owner_id
            WHERE c.user_id = {ME} AND c.status = 'pending'
            ORDER BY c.invited_at DESC
            """,
            auth0_sub,
        )
        members = await conn.fetch(
            """
            SELECT c.project_id, u.id, u.display_name
            FROM project_contributors c
            JOIN users u ON u.id = c.user_id
            WHERE c.project_id = ANY($1::uuid[]) AND c.status = 'accepted'
            ORDER BY lower(u.display_name), u.id
            """,
            [invite["id"] for invite in invites],
        )
    finally:
        await conn.close()

    accepted = {}
    for member in members:
        accepted.setdefault(member["project_id"], []).append(_user_json(member["id"], member["display_name"]))

    return [
        {
            "id": str(invite["id"]),
            "title": invite["title"],
            "thumbnail": f"/projects/{invite['id']}/thumbnail" if invite["has_thumbnail"] else None,
            "owner": _user_json(invite["owner_id"], invite["owner_name"]),
            "accepted": accepted.get(invite["id"], []),
        }
        for invite in invites
    ]


async def respond_to_invite(auth0_sub, project_id, accept):
    """Accept (become a team member) or reject (deleted) a pending invite.
    Returns the project's title, or None if there was no such pending invite."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        if accept:
            query = (
                "UPDATE project_contributors c SET status = 'accepted' FROM projects p "
                f"WHERE p.id = c.project_id AND c.project_id = $2 AND c.user_id = {ME} AND c.status = 'pending' "
                "RETURNING p.title"
            )
        else:
            query = (
                "DELETE FROM project_contributors c USING projects p "
                f"WHERE p.id = c.project_id AND c.project_id = $2 AND c.user_id = {ME} AND c.status = 'pending' "
                "RETURNING p.title"
            )
        return await conn.fetchval(query, auth0_sub, project_id)
    finally:
        await conn.close()


async def set_on_board(auth0_sub, project_id, on_board):
    """Put the logged-in user's project on the board (people can ask to collaborate) or take it off.
    Returns False if it isn't their project."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        # Adding a project that's already on the board (e.g. from a second tab) keeps its original date
        result = await conn.execute(
            f"""
            UPDATE projects
            SET board_added_at = CASE WHEN $3 THEN coalesce(board_added_at, now()) END
            WHERE id = $2 AND owner_id = {ME}
            """,
            auth0_sub, project_id, on_board,
        )
    finally:
        await conn.close()

    return result != "UPDATE 0"


async def send_thumbnail(auth0_sub, project_id):
    """Respond with a project's thumbnail, for anyone who can view the project.
    None if there's no thumbnail or the project is hidden from them."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        filename = await conn.fetchval(
            f"SELECT p.thumbnail FROM projects p WHERE p.id = $2 AND {VISIBLE_TO_ME}",
            auth0_sub, project_id,
        )
    finally:
        await conn.close()

    if not filename or not (THUMBNAIL_DIR / filename).is_file():
        return None
    return send_from_directory(THUMBNAIL_DIR, filename)


async def get_feed(auth0_sub, limit=3):
    """The newest projects created by the logged-in user's friends or teammates (anyone they share
    an accepted spot on a project with, as owner or member), newest first. Not their own projects."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        rows = await conn.fetch(
            f"""
            {CONNECTIONS_CTE}
            SELECT p.id, p.title, p.thumbnail IS NOT NULL AS has_thumbnail
            FROM projects p, me
            WHERE p.owner_id IN (SELECT id FROM connected)
              AND p.owner_id <> me.id
              AND {VISIBLE_TO_ME}
            ORDER BY p.created_at DESC, p.id
            LIMIT $2
            """,
            auth0_sub, limit,
        )
    finally:
        await conn.close()

    return [
        {
            "id": str(row["id"]),
            "title": row["title"],
            "thumbnail": f"/projects/{row['id']}/thumbnail" if row["has_thumbnail"] else None,
        }
        for row in rows
    ]


async def get_project(auth0_sub, project_id):
    """Everything /project/<id> shows: details, creator and team members (accepted invites).
    Each person has 'viewable': False if they and the viewer have blocked each other, so their
    profile isn't linked. None if the project doesn't exist or is hidden from the viewer."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        row = await conn.fetchrow(
            f"""
            SELECT p.id, p.title, p.summary, p.description, p.thumbnail IS NOT NULL AS has_thumbnail,
                   p.created_at, p.board_added_at IS NOT NULL AS on_board,
                   o.id AS owner_id, o.display_name AS owner_name, o.id = {ME} AS is_owner
            FROM projects p JOIN users o ON o.id = p.owner_id
            WHERE p.id = $2 AND {VISIBLE_TO_ME}
            """,
            auth0_sub, project_id,
        )
        if not row:
            return None
        members = await conn.fetch(
            f"""
            SELECT u.id, u.display_name,
                   NOT EXISTS (
                       SELECT 1 FROM blocks b
                       WHERE (b.blocker_id = u.id AND b.blocked_id = {ME})
                          OR (b.blocker_id = {ME} AND b.blocked_id = u.id)
                   ) AS viewable
            FROM project_contributors c JOIN users u ON u.id = c.user_id
            WHERE c.project_id = $2 AND c.status = 'accepted'
            ORDER BY lower(u.display_name), u.id
            """,
            auth0_sub, project_id,
        )
    finally:
        await conn.close()

    return {
        "id": str(row["id"]),
        "title": row["title"],
        "summary": row["summary"],
        "description": row["description"],
        "thumbnail": f"/projects/{row['id']}/thumbnail" if row["has_thumbnail"] else None,
        "created_at": row["created_at"],
        "is_owner": row["is_owner"],
        "on_board": row["on_board"],
        # Visible project = owner not blocked either way, so the owner is always viewable
        "owner": {**_user_json(row["owner_id"], row["owner_name"]), "viewable": True},
        "members": [{**_user_json(m["id"], m["display_name"]), "viewable": m["viewable"]} for m in members],
    }


PROJECTS_PER_PAGE = 6


async def get_user_projects(auth0_sub, user_id, page=1):
    """One page (up to 6, newest first) of the projects user_id has worked on: ones they created
    and ones they accepted an invite to. Projects hidden from the viewer are left out.
    None if the viewer can't see user_id's profile (blocked either way, or no such user)."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        visible_user = await conn.fetchval(
            f"""
            SELECT EXISTS (
                SELECT 1 FROM users u
                WHERE u.id = $2 AND u.about_you_completed
                  AND NOT EXISTS (
                      SELECT 1 FROM blocks b
                      WHERE (b.blocker_id = u.id AND b.blocked_id = {ME})
                         OR (b.blocker_id = {ME} AND b.blocked_id = u.id)
                  )
            )
            """,
            auth0_sub, user_id,
        )
        if not visible_user:
            return None

        worked_on = f"""
            FROM projects p
            JOIN (
                SELECT id AS project_id, 'creator' AS role FROM projects WHERE owner_id = $2
                UNION ALL
                SELECT project_id, 'contributor' FROM project_contributors WHERE user_id = $2 AND status = 'accepted'
            ) w ON w.project_id = p.id
            WHERE {VISIBLE_TO_ME}
        """
        total = await conn.fetchval(f"SELECT count(*) {worked_on}", auth0_sub, user_id)
        pages = max(1, -(-total // PROJECTS_PER_PAGE))
        page = min(max(page, 1), pages)
        rows = await conn.fetch(
            f"""
            SELECT p.id, p.title, p.thumbnail IS NOT NULL AS has_thumbnail, w.role,
                   o.id AS owner_id, o.display_name AS owner_name,
                   (SELECT count(*) FROM project_contributors c
                    WHERE c.project_id = p.id AND c.status = 'accepted') AS member_count,
                   -- First 3 members to have been invited (the ones whose pictures are shown)
                   (SELECT coalesce(json_agg(json_build_object('id', m.id, 'username', m.display_name)), '[]')
                    FROM (
                        SELECT u.id, u.display_name
                        FROM project_contributors c JOIN users u ON u.id = c.user_id
                        WHERE c.project_id = p.id AND c.status = 'accepted'
                        ORDER BY c.invited_at, lower(u.display_name), u.id
                        LIMIT 3
                    ) m) AS first_members
            {worked_on.replace("FROM projects p", "FROM projects p JOIN users o ON o.id = p.owner_id", 1)}
            ORDER BY p.created_at DESC, p.id
            LIMIT $3 OFFSET $4
            """,
            auth0_sub, user_id, PROJECTS_PER_PAGE, (page - 1) * PROJECTS_PER_PAGE,
        )
    finally:
        await conn.close()

    return {
        "page": page,
        "pages": pages,
        "projects": [
            {
                "id": str(row["id"]),
                "title": row["title"],
                "thumbnail": f"/projects/{row['id']}/thumbnail" if row["has_thumbnail"] else None,
                "role": row["role"],
                # Up to 4 pictures: creator + first 3 members; extra = members not pictured ("+N")
                "people": [_user_json(row["owner_id"], row["owner_name"])] + [
                    _user_json(member["id"], member["username"]) for member in json.loads(row["first_members"])
                ],
                "extra": max(0, row["member_count"] - 3),
            }
            for row in rows
        ],
    }


async def get_project_for_edit(auth0_sub, project_id):
    """The project's current values plus every teammate (members and pending invites) for the
    edit form. None unless the logged-in user owns it."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        row = await conn.fetchrow(
            f"""
            SELECT id, title, summary, description, thumbnail IS NOT NULL AS has_thumbnail
            FROM projects WHERE id = $2 AND owner_id = {ME}
            """,
            auth0_sub, project_id,
        )
        if not row:
            return None
        teammates = await conn.fetch(
            """
            SELECT u.id, u.display_name, c.status
            FROM project_contributors c JOIN users u ON u.id = c.user_id
            WHERE c.project_id = $1
            ORDER BY lower(u.display_name), u.id
            """,
            project_id,
        )
    finally:
        await conn.close()

    return {
        "id": str(row["id"]),
        "title": row["title"],
        "summary": row["summary"],
        "description": row["description"] or "",
        "thumbnail": f"/projects/{row['id']}/thumbnail" if row["has_thumbnail"] else None,
        "teammates": [{**_user_json(t["id"], t["display_name"]), "status": t["status"]} for t in teammates],
    }


def _user_json(user_id, username):
    return {"id": str(user_id), "username": username, "picture": f"/users/{user_id}/picture"}
