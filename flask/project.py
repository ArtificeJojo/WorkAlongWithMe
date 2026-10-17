import asyncpg
from os import environ as env
from pathlib import Path
from uuid import UUID, uuid4

from flask import send_from_directory

import profile
from connection import ME

THUMBNAIL_DIR = profile.ROOT / "uploads" / "project_thumbnails"
MAX_LENGTHS = {"title": 100, "summary": 300, "description": 10000}


class ProjectError(ValueError):
    """Bad project submission. missing lists the mandatory fields that were left empty."""

    def __init__(self, message, missing=()):
        super().__init__(message)
        self.missing = list(missing)


async def create_project(auth0_sub, title, summary, description, thumbnail, contributor_ids):
    """Create a project owned by the logged-in user, with the teammates they picked.
    thumbnail is an uploaded file or None. Returns the new project's id.
    Raises ProjectError if a mandatory field is empty or anything else is invalid."""
    title = (title or "").strip()
    summary = (summary or "").strip()
    description = (description or "").strip() or None

    missing = [field for field, value in (("title", title), ("summary", summary)) if not value]
    if missing:
        raise ProjectError("Some mandatory fields have not been completed", missing)

    for field, value in (("title", title), ("summary", summary), ("description", description)):
        if value and len(value) > MAX_LENGTHS[field]:
            raise ProjectError(f"The {field} is too long ({MAX_LENGTHS[field]} characters max)")

    try:
        contributors = list({UUID(user_id) for user_id in contributor_ids})
    except ValueError:
        raise ProjectError("Some teammates can't be added")

    thumbnail_name = None
    if thumbnail and thumbnail.filename:
        extension = Path(thumbnail.filename).suffix.lower()
        if extension not in profile.ALLOWED_EXTENSIONS:
            raise ProjectError("The thumbnail must be a .jpg, .jpeg, .png, .gif or .webp file")
        THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
        thumbnail_name = uuid4().hex + extension
        thumbnail.save(THUMBNAIL_DIR / thumbnail_name)

    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        async with conn.transaction():
            # Teammates must be real users who finished /aboutyou, not you, and not blocked either way
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
                auth0_sub, contributors,
            )
            if allowed != len(contributors):
                raise ProjectError("Some teammates can't be added")

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


async def send_thumbnail(auth0_sub, project_id):
    """Respond with a project's thumbnail, for its owner and anyone invited to it.
    None if there's no thumbnail or the user isn't part of the project."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        filename = await conn.fetchval(
            f"""
            SELECT p.thumbnail FROM projects p
            WHERE p.id = $2
              AND (p.owner_id = {ME}
                   OR EXISTS (SELECT 1 FROM project_contributors c WHERE c.project_id = p.id AND c.user_id = {ME}))
            """,
            auth0_sub, project_id,
        )
    finally:
        await conn.close()

    if not filename or not (THUMBNAIL_DIR / filename).is_file():
        return None
    return send_from_directory(THUMBNAIL_DIR, filename)


def _user_json(user_id, username):
    return {"id": str(user_id), "username": username, "picture": f"/users/{user_id}/picture"}
