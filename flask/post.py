import asyncpg
import shutil
from os import environ as env
from pathlib import Path
from uuid import UUID, uuid4

from flask import send_from_directory

import profile
from connection import ME
import project
from project import CONNECTIONS_CTE

IMAGE_DIR = profile.ROOT / "uploads" / "post_images"
MAX_CHARACTERS = 250

# Post p can be seen by the logged-in user unless they and its author have blocked each other
VISIBLE_TO_ME = f"""
    NOT EXISTS (
        SELECT 1 FROM blocks b
        WHERE (b.blocker_id = p.author_id AND b.blocked_id = {ME})
           OR (b.blocker_id = {ME} AND b.blocked_id = p.author_id)
    )
"""


# Project $2 was created or joined (accepted invite) by the logged-in user ($1)
MY_PROJECT = f"""
    EXISTS (
        SELECT 1 FROM projects pr
        WHERE pr.id = $2
          AND (pr.owner_id = {ME}
               OR EXISTS (SELECT 1 FROM project_contributors c
                          WHERE c.project_id = pr.id AND c.user_id = {ME} AND c.status = 'accepted'))
    )
"""


class PostError(ValueError):
    """Bad post submission. missing lists the fields to highlight when the post is empty."""

    def __init__(self, message, missing=()):
        super().__init__(message)
        self.missing = list(missing)


async def create_post(auth0_sub, body, image, project_id=None, use_project_thumbnail=False):
    """Publish a post by the logged-in user: up to 250 characters of text and/or one image (at
    least one), optionally linking a project they created or joined.
    use_project_thumbnail copies the linked project's thumbnail as the post's image (instead of
    an uploaded one), so the post keeps it even if the project's thumbnail changes later.
    Returns the new post's id. Raises PostError if it's empty or invalid."""
    body = (body or "").strip() or None
    has_image = bool(image and image.filename) and not use_project_thumbnail

    if not body and not has_image and not use_project_thumbnail:
        raise PostError("Add some text or an image before posting", ["body", "image"])
    if body and len(body) > MAX_CHARACTERS:
        raise PostError(f"Posts can be at most {MAX_CHARACTERS} characters", ["body"])
    try:
        project_id = UUID(project_id) if project_id else None
    except ValueError:
        raise PostError("You can only link projects you created or joined", ["project"])
    if use_project_thumbnail and not project_id:
        raise PostError("Link a project to use its thumbnail", ["project"])

    image_name = None
    if has_image:
        extension = Path(image.filename).suffix.lower()
        if extension not in profile.ALLOWED_EXTENSIONS:
            raise PostError("The image must be a .jpg, .jpeg, .png, .gif or .webp file", ["image"])
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        image_name = uuid4().hex + extension
        image.save(IMAGE_DIR / image_name)

    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        async with conn.transaction():
            if project_id and not await conn.fetchval(f"SELECT {MY_PROJECT}", auth0_sub, project_id):
                raise PostError("You can only link projects you created or joined", ["project"])

            if use_project_thumbnail:
                thumbnail = await conn.fetchval("SELECT thumbnail FROM projects WHERE id = $1", project_id)
                if not thumbnail or not (project.THUMBNAIL_DIR / thumbnail).is_file():
                    raise PostError("That project doesn't have a thumbnail", ["project"])
                IMAGE_DIR.mkdir(parents=True, exist_ok=True)
                image_name = uuid4().hex + Path(thumbnail).suffix
                shutil.copyfile(project.THUMBNAIL_DIR / thumbnail, IMAGE_DIR / image_name)

            return await conn.fetchval(
                f"INSERT INTO posts (author_id, body, image, project_id) VALUES ({ME}, $2, $3, $4) RETURNING id",
                auth0_sub, body, image_name, project_id,
            )
    except Exception:
        if image_name:
            (IMAGE_DIR / image_name).unlink(missing_ok=True)
        raise
    finally:
        await conn.close()


async def get_linkable_projects(auth0_sub):
    """Projects the logged-in user created or joined, for the "Link a project" dropdown."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        rows = await conn.fetch(
            f"""
            SELECT pr.id, pr.title, pr.thumbnail IS NOT NULL AS has_thumbnail FROM projects pr
            WHERE pr.owner_id = {ME}
               OR EXISTS (SELECT 1 FROM project_contributors c
                          WHERE c.project_id = pr.id AND c.user_id = {ME} AND c.status = 'accepted')
            ORDER BY lower(pr.title), pr.id
            """,
            auth0_sub,
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


async def get_feed(auth0_sub, limit=3):
    """The newest posts by the logged-in user, their friends or their teammates, newest first."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        rows = await conn.fetch(
            f"""
            {CONNECTIONS_CTE}
            SELECT p.id, p.body, p.image IS NOT NULL AS has_image, p.created_at,
                   u.id AS author_id, u.display_name AS author_name,
                   -- Linked project, only if the viewer can see it (its owner isn't blocked either way)
                   lp.id AS project_id, lp.title AS project_title
            FROM posts p
            JOIN users u ON u.id = p.author_id
            LEFT JOIN projects lp ON lp.id = p.project_id AND NOT EXISTS (
                SELECT 1 FROM blocks b
                WHERE (b.blocker_id = lp.owner_id AND b.blocked_id = {ME})
                   OR (b.blocker_id = {ME} AND b.blocked_id = lp.owner_id)
            ),
            me
            WHERE (p.author_id = me.id OR p.author_id IN (SELECT id FROM connected))
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
            "body": row["body"],
            "image": f"/posts/{row['id']}/image" if row["has_image"] else None,
            "created_at": row["created_at"],
            "project": {"id": str(row["project_id"]), "title": row["project_title"]} if row["project_id"] else None,
            "author": {
                "id": str(row["author_id"]),
                "username": row["author_name"],
                "picture": f"/users/{row['author_id']}/picture",
            },
        }
        for row in rows
    ]


async def send_image(auth0_sub, post_id):
    """Respond with a post's image, unless the viewer and the author have blocked each other.
    None if there's no image or it's hidden from them."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        filename = await conn.fetchval(
            f"SELECT p.image FROM posts p WHERE p.id = $2 AND {VISIBLE_TO_ME}",
            auth0_sub, post_id,
        )
    finally:
        await conn.close()

    if not filename or not (IMAGE_DIR / filename).is_file():
        return None
    return send_from_directory(IMAGE_DIR, filename)
