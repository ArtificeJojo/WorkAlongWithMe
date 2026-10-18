import asyncpg
from dotenv import load_dotenv
from os import environ as env

from auth0_server_python.auth_server.server_client import ServerClient
from auth0_server_python.auth_types import LogoutOptions, StartInteractiveLoginOptions, StateData, TransactionData
from auth0_server_python.store.abstract import AbstractDataStore

from flask import Flask, request, redirect, url_for, render_template, render_template_string, after_this_request, jsonify, send_from_directory
import asyncio
from markupsafe import escape
from urllib.parse import urlencode, urlparse
from uuid import UUID

import profile
import connection
import project
import post
import likes
import quests
import matching
import party
import skills

load_dotenv()
app = Flask(__name__)

# Everyone plays both quest tracks in order (Gators, then Turtle), so /aboutyou no longer picks one.
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload limit (profile pictures)


@app.route("/")
def start():
    asyncio.run(main())
    
    with open("..\\src\\index.html", encoding="utf-8") as html:
    
        return html.read()

@app.route("/Images/<path:filename>")
def site_image(filename):
    # Shared site images (e.g. the bg.png page background). Public, since the login page uses them too.
    # send_from_directory refuses paths that try to escape the folder (e.g. ../.env)
    return send_from_directory(profile.ROOT / "Images", filename)

@app.route("/js/<path:filename>")
def site_script(filename):
    # Shared page scripts (e.g. pixel.js, the animated pixel characters)
    return send_from_directory(profile.ROOT / "src" / "js", filename)

@app.route("/favicon.ico")
def favicon():
    # Every page links here; browsers also ask for it on pages without a <link rel="icon">, e.g. plain-text error pages.
    # A square multi-size .ico (made from LogoNoBg.png) works in both Chrome and Firefox
    return send_from_directory(profile.ROOT / "Images", "favicon.ico", mimetype="image/x-icon")

@app.route("/login")
async def login():
    # The login cookie (_a0_tx) only reaches /callback on the same host, and Auth0 always calls
    # back to APP_BASE_URL, so start the login there (e.g. if a link still points at an old ngrok URL)
    # Compare hosts only: behind the Cloudflare tunnel Flask sees http even though visitors use https
    base_url = env.get("APP_BASE_URL", "").rstrip("/")
    if request.host != urlparse(base_url).netloc:
        return redirect(base_url + request.full_path.rstrip("?"))

    url = await auth0().start_interactive_login(
        options=StartInteractiveLoginOptions(
            authorization_params=dict(request.args),
        ),
        store_options={"request": request},
    )
    
    print(url)
    return redirect(url)

@app.route("/callback")
async def callback():
    try:
        result = await auth0().complete_interactive_login(
            request.url,
            store_options={"request": request},
        )
        step = await register_user(result["state_data"]["user"])
    except Exception as e:
        # Send the error back to index.html, which already displays ?error= params
        app.logger.warning("Login callback failed", exc_info=True)
        return redirect("/?" + urlencode({"error": "login_failed", "error_description": str(e)}))

    # Keep sending them to /aboutyou until they've submitted the form
    return redirect(step or "/home")


class CookieStore(AbstractDataStore):
    def __init__(self, secret, cookie_name, max_age, model):
        super().__init__({"secret": secret})
        self.cookie_name = cookie_name
        self.max_age = max_age
        self.model = model

    async def set(self, identifier, state, **_):
        @after_this_request
        def apply(response):
            data = state.model_dump() if hasattr(state, "model_dump") else state
            response.set_cookie(
                self.cookie_name,
                self.encrypt(identifier, data),
                httponly=True,
                samesite="Lax",
                secure=not env.get("APP_BASE_URL", "").startswith("http://"),
                max_age=self.max_age,
            )
            return response

    async def get(self, identifier, options=None):
        try:
            if options: encrypted = options["request"].cookies.get(self.cookie_name)
            return self.model.model_validate(self.decrypt(identifier, encrypted)) if encrypted else None
        except Exception:
            app.logger.warning("Failed to decrypt cookie %s", self.cookie_name, exc_info=True)
            return None

    async def delete(self, *_, **__):
        @after_this_request
        def apply(response):
            response.delete_cookie(self.cookie_name)
            return response



@app.route("/logout")
async def logout():
    url = await auth0().logout(
        options=LogoutOptions(return_to=env.get("APP_BASE_URL")),
        store_options={"request": request},
    )
    return redirect(url)

@app.route("/home")
async def home():
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return redirect("/")
    about_you = await get_about_you(user["sub"])
    if step := setup_step(about_you):
        return redirect(step)

    with open("..\\src\\home.html", encoding="utf-8") as html:

        return render_template_string(
            html.read(),
            username=about_you["display_name"],
            organization=about_you["organization"],
            projects=await project.get_feed(user["sub"]),
            posts=await post.get_feed(user["sub"]),
            # Board tab: the 5 most recently added; "See more" goes to /board
            board=(await project.get_board(user["sub"], per_page=5))["projects"],
            # Yellow/red "View profile" until they've seen an answered collaborator request on /profile
            profile_highlight=await project.request_update_highlight(user["sub"]),
            quest_cards=await quest_cards(user["sub"]),
        )

@app.route("/board")
async def board():
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return redirect("/")
    if step := await setup_redirect(user["sub"]):
        return redirect(step)

    with open("..\\src\\board.html", encoding="utf-8") as html:

        return render_template_string(html.read(), board=await project.get_board(user["sub"], request.args.get("page", 1, type=int)))

@app.route("/profile")
async def view_profile():
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return redirect("/")
    about_you = await get_about_you(user["sub"])
    if step := setup_step(about_you):
        return redirect(step)

    with open("..\\src\\profile.html", encoding="utf-8") as html:

        return render_template_string(
            html.read(),
            username=about_you["display_name"],
            user_id=str(about_you["id"]),
            skills=about_you["skills"],
            has_custom_picture=await profile.has_custom_profile_picture(user["sub"]),
            has_invites=await project.has_pending_invites(user["sub"]),
            # Answered collaborator requests, shown once: rejections as messages, acceptances highlighted
            request_updates=await project.take_request_updates(user["sub"]),
            # Projects they were on that the creator deleted, shown once
            deleted_projects=await project.take_deletion_notices(user["sub"]),
        )

@app.route("/connections")
async def connections():
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return redirect("/")
    if step := await setup_redirect(user["sub"]):
        return redirect(step)

    with open("..\\src\\connections.html", encoding="utf-8") as html:

        return html.read()

@app.route("/profile-picture", methods=["GET", "POST", "DELETE"])
async def profile_picture():
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return "Not logged in", 401

    if request.method == "POST":
        try:
            await profile.replace_profile_picture(user["sub"], request.files["picture"])
        except (KeyError, ValueError) as e:
            return str(e), 400
        return "", 204

    if request.method == "DELETE":
        await profile.reset_profile_picture(user["sub"])
        return "", 204

    return await profile.send_profile_picture(user["sub"])

@app.route("/users/search")
async def search_users():
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return "Not logged in", 401

    # connections.html asks for 7; cap it so nobody can list every user
    limit = min(request.args.get("limit", 4, type=int), 7)
    # project_create.html leaves out teammates it already added (?exclude=<id>&exclude=<id>...)
    try:
        exclude = [UUID(user_id) for user_id in request.args.getlist("exclude")]
    except ValueError:
        return "Invalid user id in exclude", 400
    return jsonify(await connection.search_users(user["sub"], request.args.get("q", ""), max(limit, 1), exclude))

@app.route("/friends")
async def friends():
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return "Not logged in", 401

    return jsonify(await connection.get_connections(user["sub"]))

@app.route("/friends/requests/<uuid:user_id>", methods=["POST"])
async def send_friend_request(user_id):
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return "Not logged in", 401

    try:
        relationship = await connection.send_friend_request(user["sub"], user_id)
    except ValueError as e:
        return str(e), 400
    return jsonify({"relationship": relationship})

@app.route("/friends/requests/<uuid:user_id>/<any(accept, reject):action>", methods=["POST"])
async def respond_to_friend_request(user_id, action):
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return "Not logged in", 401

    if not await connection.respond_to_friend_request(user["sub"], user_id, accept=action == "accept"):
        return "No pending friend request from that user", 404
    return "", 204

@app.route("/friends/<uuid:user_id>", methods=["DELETE"])
async def remove_friend(user_id):
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return "Not logged in", 401

    if not await connection.remove_friend(user["sub"], user_id):
        return "You aren't friends with that user", 404
    return "", 204

@app.route("/blocks/<uuid:user_id>", methods=["POST", "DELETE"])
async def block(user_id):
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return "Not logged in", 401

    if request.method == "DELETE":
        if not await connection.unblock_user(user["sub"], user_id):
            return "You haven't blocked that user", 404
        return "", 204

    try:
        await connection.block_user(user["sub"], user_id)
    except ValueError as e:
        return str(e), 400
    return "", 204

@app.route("/friends/seen", methods=["POST"])
async def mark_new_friends_seen():
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return "Not logged in", 401

    await connection.mark_new_friends_seen(user["sub"])
    return "", 204

@app.route("/users/<uuid:user_id>/picture")
async def user_picture(user_id):
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return "Not logged in", 401

    return await connection.send_profile_picture_by_id(user["sub"], user_id)

@app.route("/project_create", methods=["GET", "POST"])
async def project_create():
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return redirect("/") if request.method == "GET" else ("Not logged in", 401)
    if step := await setup_redirect(user["sub"]):
        return redirect(step) if request.method == "GET" else ("Finish /aboutyou first", 403)

    if request.method == "POST":
        try:
            project_id = await project.create_project(
                user["sub"],
                request.form.get("title"),
                request.form.get("summary"),
                request.form.get("description"),
                request.files.get("thumbnail"),
                request.form.getlist("contributors"),
            )
        except project.ProjectError as e:
            return jsonify({"error": str(e), "missing": e.missing}), 400
        return jsonify({"id": str(project_id)}), 201

    with open("..\\src\\project_create.html", encoding="utf-8") as html:

        return render_template_string(html.read(), project=None)

@app.route("/project/<uuid:project_id>/edit", methods=["GET", "POST"])
async def project_edit(project_id):
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return redirect("/") if request.method == "GET" else ("Not logged in", 401)
    if step := await setup_redirect(user["sub"]):
        return redirect(step) if request.method == "GET" else ("Finish /aboutyou first", 403)

    if request.method == "POST":
        try:
            updated = await project.update_project(
                user["sub"],
                project_id,
                request.form.get("title"),
                request.form.get("summary"),
                request.form.get("description"),
                request.files.get("thumbnail"),
                request.form.get("removeThumbnail") == "true",
                request.form.getlist("contributors"),
            )
        except project.ProjectError as e:
            return jsonify({"error": str(e), "missing": e.missing}), 400
        if not updated:
            return jsonify({"error": "You can only edit your own projects", "missing": []}), 404
        return jsonify({"id": str(project_id)})

    details = await project.get_project_for_edit(user["sub"], project_id)
    if not details:
        return "Project not found", 404

    # Same form as creating a project, filled in with the current values
    with open("..\\src\\project_create.html", encoding="utf-8") as html:

        return render_template_string(html.read(), project=details)

@app.route("/users/<uuid:user_id>/projects")
async def user_projects(user_id):
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return "Not logged in", 401

    projects = await project.get_user_projects(user["sub"], user_id, request.args.get("page", 1, type=int))
    if projects is None:
        return "User not found", 404
    return jsonify(projects)

@app.route("/project/<uuid:project_id>")
async def view_project(project_id):
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return redirect("/")
    if step := await setup_redirect(user["sub"]):
        return redirect(step)

    details = await project.get_project(user["sub"], project_id)
    if not details:
        return "Project not found", 404

    with open("..\\src\\project.html", encoding="utf-8") as html:

        return render_template_string(html.read(), project=details)

@app.route("/create_post", methods=["GET", "POST"])
async def create_post():
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return redirect("/") if request.method == "GET" else ("Not logged in", 401)
    if step := await setup_redirect(user["sub"]):
        return redirect(step) if request.method == "GET" else ("Finish /aboutyou first", 403)

    if request.method == "POST":
        try:
            post_id = await post.create_post(
                user["sub"], request.form.get("body"), request.files.get("image"), request.form.get("project"),
                use_project_thumbnail=request.form.get("useProjectThumbnail") == "true",
            )
        except post.PostError as e:
            return jsonify({"error": str(e), "missing": e.missing}), 400
        return jsonify({"id": str(post_id)}), 201

    with open("..\\src\\create_post.html", encoding="utf-8") as html:

        return render_template_string(html.read(), projects=await post.get_linkable_projects(user["sub"]))

@app.route("/posts/<uuid:post_id>", methods=["DELETE"])
async def delete_post(post_id):
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return "Not logged in", 401

    if not await post.delete_post(user["sub"], post_id):
        return "You can only delete your own posts", 404
    return jsonify({"deleted": True})

@app.route("/posts/<uuid:post_id>/image")
async def post_image(post_id):
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return "Not logged in", 401

    return await post.send_image(user["sub"], post_id) or ("No image", 404)

@app.route("/invites")
async def invites():
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return redirect("/")
    if step := await setup_redirect(user["sub"]):
        return redirect(step)

    with open("..\\src\\invites.html", encoding="utf-8") as html:

        return html.read()

@app.route("/projects/invites")
async def project_invites():
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return "Not logged in", 401

    return jsonify(await project.get_invites(user["sub"]))

@app.route("/projects/<uuid:project_id>/invite/<any(accept, reject):action>", methods=["POST"])
async def respond_to_project_invite(project_id, action):
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return "Not logged in", 401

    title = await project.respond_to_invite(user["sub"], project_id, accept=action == "accept")
    if title is None:
        return "No pending invite to that project", 404
    return jsonify({"title": title})

@app.route("/projects/<uuid:project_id>/board", methods=["POST", "DELETE"])
async def project_board(project_id):
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return "Not logged in", 401

    # POST puts the project on the board, DELETE takes it off
    if not await project.set_on_board(user["sub"], project_id, request.method == "POST"):
        return "You can only change the board for your own projects", 404
    return jsonify({"onBoard": request.method == "POST"})

@app.route("/projects/<uuid:project_id>", methods=["DELETE"])
async def delete_project(project_id):
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return "Not logged in", 401

    result = await project.delete_project(user["sub"], project_id)
    if result == "on_board":
        return "Take the project off the board before deleting it", 409
    if not result:
        return "You can only delete your own projects", 404
    return jsonify({"deleted": True})

@app.route("/projects/<uuid:project_id>/collaborate", methods=["POST"])
async def request_to_collaborate(project_id):
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return "Not logged in", 401

    result = await project.request_to_collaborate(user["sub"], project_id)
    if result == "full":
        return "This project already has the maximum number of pending requests", 409
    if not result:
        return "You can't request to collaborate on this project", 404
    return jsonify({"requested": True})

@app.route("/requests/<uuid:project_id>")
async def collaborator_requests(project_id):
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return redirect("/")
    if step := await setup_redirect(user["sub"]):
        return redirect(step)

    details = await project.get_requests(user["sub"], project_id)
    if not details:
        return "Project not found", 404

    with open("..\\src\\requests.html", encoding="utf-8") as html:

        return render_template_string(html.read(), project=details)

@app.route("/projects/<uuid:project_id>/requests/<uuid:user_id>/<any(accept, reject):action>", methods=["POST"])
async def respond_to_collaborator_request(project_id, user_id, action):
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return "Not logged in", 401

    if not await project.respond_to_request(user["sub"], project_id, user_id, accept=action == "accept"):
        return "No pending request from that user", 404
    return jsonify({"status": "accepted" if action == "accept" else "rejected"})

@app.route("/<any(posts, projects):kind>/<uuid:item_id>/like", methods=["POST", "DELETE"])
async def like(kind, item_id):
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return "Not logged in", 401

    # POST likes it, DELETE takes the like back
    result = await likes.set_like(user["sub"], kind.rstrip("s"), item_id, request.method == "POST")
    if result is None:
        return "Not found", 404
    return jsonify(result)

@app.route("/projects/<uuid:project_id>/thumbnail")
async def project_thumbnail(project_id):
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return "Not logged in", 401

    return await project.send_thumbnail(user["sub"], project_id) or ("No thumbnail", 404)

@app.route("/friend/<uuid:user_id>")
async def view_other_profile(user_id):
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return redirect("/")
    if step := await setup_redirect(user["sub"]):
        return redirect(step)

    other = await connection.get_user_profile(user["sub"], user_id)
    if not other:
        return "User not found", 404
    if other["relationship"] == "self":
        return redirect("/profile")

    with open("..\\src\\friend.html", encoding="utf-8") as html:

        return render_template_string(html.read(), user=other)

@app.route("/aboutyou", methods=["GET", "POST"])
async def about_you():
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return redirect("/")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        organization = request.form.get("organization", "").strip()
        technical_skills = skills.clean(request.form.getlist("skills"))
        if not username or not organization or not technical_skills:
            return redirect("/aboutyou")

        conn = await asyncpg.connect(env.get("DATABASE_URL"))
        try:
            await conn.execute(
                "UPDATE users SET display_name = $1, organization = $2, skills = $3, about_you_completed = TRUE "
                "WHERE auth0_sub = $4",
                username, organization, technical_skills, user["sub"],
            )
        finally:
            await conn.close()

        return redirect("/home")

    # Pre-fill whatever they've answered before
    about_you = await get_about_you(user["sub"])
    with open("..\\src\\about_you.html", encoding="utf-8") as html:

        return render_template_string(
            html.read(), about_you=about_you or {},
            skill_suggestions=skills.suggestions(), max_skills=skills.MAX_SKILLS, max_skill_length=skills.MAX_LENGTH,
        )

@app.route("/quest")
async def quest_start():
    """Sends the student to their next unfinished quest, or the Tavern once both are done."""
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return redirect("/")
    progress = await quests.get_progress(user["sub"])
    next_id = quests.next_quest(progress["completed"] if progress else [])
    return redirect(f"/quest/{next_id}" if next_id else "/tavern")

@app.route("/quest/<quest_id>")
async def quest_page(quest_id):
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return redirect("/")
    # Quests are part of setup, so only /aboutyou has to be done first
    if step := setup_step(await get_about_you(user["sub"])):
        return redirect(step)
    if quest_id not in quests.QUESTS:
        return "Quest not found", 404

    progress = await quests.get_progress(user["sub"])
    if quest_id not in progress["unlocked"]:
        # Turtle opens after Gators: send them to the quest they still need
        return redirect(f"/quest/{quests.next_quest(progress['completed'])}")

    with open("..\\src\\quest.html", encoding="utf-8") as html:

        return render_template_string(
            html.read(),
            quest_id=quest_id,
            quests_json=quests.quests_json(),
            progress_json=quests.to_script_json(progress),
        )

@app.route("/quest/<quest_id>/finish", methods=["POST"])
async def quest_finish(quest_id):
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return jsonify({"error": "Not logged in"}), 401

    body = request.get_json(silent=True) or {}
    try:
        progress = await quests.finish_quest(user["sub"], quest_id, body.get("answers") or {}, body.get("visibility") or {})
    except quests.QuestError as e:
        return jsonify({"error": str(e)}), 400
    quest = quests.QUESTS[quest_id]
    return jsonify({"progress": progress, "summary": quests.summarize(quest, progress["answers"])})

@app.route("/quest-progress")
async def quest_progress():
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return jsonify({"error": "Not logged in"}), 401
    return jsonify(await quests.get_progress(user["sub"]))

@app.route("/tavern")
async def tavern():
    """Top matches (rules pick them, Gemini words them) and a form to start a party."""
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return redirect("/")
    if step := await setup_redirect(user["sub"]):
        return redirect(step)
    progress = await quests.get_progress(user["sub"])

    me, matches = await matching.matches_for(user["sub"], n=4)
    if not me:
        return redirect("/quest")
    # Rule-based reasons now; the page then asks /tavern/why for Gemini's wording, so it opens straight away
    matches = party.plain_reasons(matches)
    for m in matches:
        m["chips"] = party.chips(m["hero"])
    with open("..\\src\\tavern.html", encoding="utf-8") as html:

        return render_template_string(
            html.read(),
            matches=matches,
            parties=await party.my_parties(user["sub"]),
            both_done=all(q in progress["completed"] for q in quests.QUEST_ORDER),
            # Only wait for Gemini when there's something for it to word
            gemini_pending=any(m["reasons"] for m in matches),
        )

@app.route("/tavern/why")
async def tavern_why():
    """Gemini's friendlier 'why' sentence for each match on /tavern, by user id. Slow (Gemini), so the
    page loads first and fetches this; empty if Gemini isn't available, so the plain reasons stay."""
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return jsonify({"error": "Not logged in"}), 401

    me, matches = await matching.matches_for(user["sub"], n=4)
    if not me:
        return jsonify({"why": {}})
    sentences = party.gemini_reasons(me["display_name"], matches) or []
    return jsonify({"why": {m["hero"]["user_id"]: s for m, s in zip(matches, sentences) if s}})

@app.route("/tavern/party", methods=["POST"])
async def form_party():
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return jsonify({"error": "Not logged in"}), 401
    body = request.get_json(silent=True) or {}
    try:
        group_id = await party.create_party(user["sub"], body.get("teammates") or [], body.get("name"))
    except party.PartyError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"id": group_id}), 201

@app.route("/party/<uuid:group_id>/pact", methods=["POST"])
async def finish_party_pact(group_id):
    """Gemini's Party Pact for a newly formed party (slow, so the party page loads first and calls this)."""
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return jsonify({"error": "Not logged in"}), 401
    pact = await party.finish_pact(user["sub"], group_id)
    if pact is None:
        return jsonify({"error": "Party not found"}), 404
    return jsonify(pact)

@app.route("/party/<uuid:group_id>")
async def view_party(group_id):
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return redirect("/")
    details = await party.get_party(user["sub"], group_id)
    if not details:
        return "Party not found", 404
    with open("..\\src\\party.html", encoding="utf-8") as html:

        return render_template_string(html.read(), party=details)

async def quest_cards(auth0_sub):
    """One card per quest for /home: done, open (next up) or locked."""
    progress = await quests.get_progress(auth0_sub)
    completed = progress["completed"] if progress else []
    unlocked = quests.unlocked_quests(completed)
    cards = []
    for quest_id in quests.QUEST_ORDER:
        q = quests.QUESTS[quest_id]
        status = "done" if quest_id in completed else "open" if quest_id in unlocked else "locked"
        cards.append({
            "id": quest_id, "name": q["name"], "card": q["card"],
            "badge": q["badge"], "status": status,
        })
    return cards

async def register_user(user):
    """Create a users row for this Auth0 account if there isn't one yet.
    Returns where to send them to finish setup (see setup_step), or None if they're done."""
    display_name = user.get("name") or user.get("nickname") or user.get("email") or user["sub"]

    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        await conn.execute(
            "INSERT INTO users (display_name, auth0_sub) VALUES ($1, $2) "
            "ON CONFLICT (auth0_sub) DO NOTHING",
            display_name, user["sub"],
        )
    finally:
        await conn.close()

    return await setup_redirect(user["sub"])

def setup_step(about_you):
    """First-time setup is the /aboutyou form, including at least one technical skill
    (users who finished it before skills were added go back once). Returns "/aboutyou" until it's done, then None."""
    if not about_you or not about_you["about_you_completed"] or not about_you["skills"]:
        return "/aboutyou"
    return None

async def setup_redirect(auth0_sub):
    return setup_step(await get_about_you(auth0_sub))

async def get_about_you(auth0_sub):
    """Returns the user's /aboutyou answers and setup flags, or None if they have no row."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        return await conn.fetchrow(
            "SELECT id, display_name, organization, track, about_you_completed, skills "
            "FROM users WHERE auth0_sub = $1", auth0_sub,
        )
    finally:
        await conn.close()

async def main():
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    extensions = await conn.fetch("select current_date")
    for extension in extensions:
        print(extension)
    await conn.close()



def auth0():
    session_secret = env.get("AUTH0_SECRET")
    
    return ServerClient(
        domain=env.get("AUTH0_DOMAIN"),
        client_id=env.get("AUTH0_CLIENT_ID"),
        client_secret=env.get("AUTH0_CLIENT_SECRET"),
        redirect_uri=env.get("APP_BASE_URL") + "/callback",
        authorization_params={"scope": "openid profile email"},
        secret=session_secret,
        state_store=CookieStore(session_secret, "_a0_session", 259200, StateData),  # 3 days
        transaction_store=CookieStore(session_secret, "_a0_tx", 300, TransactionData),  # 5 min
    )


if __name__ == "__main__":
    app.run()