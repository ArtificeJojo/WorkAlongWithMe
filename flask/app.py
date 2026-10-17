import asyncpg
from dotenv import load_dotenv
from os import environ as env

from auth0_server_python.auth_server.server_client import ServerClient
from auth0_server_python.auth_types import LogoutOptions, StartInteractiveLoginOptions, StateData, TransactionData
from auth0_server_python.store.abstract import AbstractDataStore

from flask import Flask, request, redirect, url_for, render_template, render_template_string, after_this_request
import asyncio
from markupsafe import escape
from urllib.parse import urlencode

import profile

load_dotenv()
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload limit (profile pictures)


@app.route("/")
def start():
    asyncio.run(main())
    
    with open("..\\src\\index.html") as html:
    
        return html.read()

@app.route("/login")
async def login():
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
        completed = await register_user(result["state_data"]["user"])
    except Exception as e:
        # Send the error back to index.html, which already displays ?error= params
        app.logger.warning("Login callback failed", exc_info=True)
        return redirect("/?" + urlencode({"error": "login_failed", "error_description": str(e)}))

    # Keep sending them to /aboutyou until they've submitted the form
    return redirect("/home" if completed else "/aboutyou")


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
    if not about_you or not about_you["about_you_completed"]:
        return redirect("/aboutyou")

    with open("..\\src\\home.html") as html:

        return render_template_string(html.read(), organization=about_you["organization"])

@app.route("/profile-picture", methods=["GET", "POST"])
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

    return await profile.send_profile_picture(user["sub"])

@app.route("/aboutyou", methods=["GET", "POST"])
async def about_you():
    user = await auth0().get_user(store_options={"request": request})
    if not user:
        return redirect("/")

    if request.method == "POST":
        organization = request.form.get("organization", "").strip()
        if not organization:
            return redirect("/aboutyou")

        conn = await asyncpg.connect(env.get("DATABASE_URL"))
        try:
            await conn.execute(
                "UPDATE users SET organization = $1, about_you_completed = TRUE WHERE auth0_sub = $2",
                organization, user["sub"],
            )
        finally:
            await conn.close()

        return redirect("/home")

    with open("..\\src\\about_you.html") as html:

        return html.read()

async def register_user(user):
    """Create a users row for this Auth0 account if there isn't one yet.
    Returns whether they've completed the /aboutyou form."""
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

    about_you = await get_about_you(user["sub"])
    return bool(about_you and about_you["about_you_completed"])

async def get_about_you(auth0_sub):
    """Returns the user's /aboutyou answers and completion flag, or None if they have no row."""
    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        return await conn.fetchrow(
            "SELECT organization, about_you_completed FROM users WHERE auth0_sub = $1", auth0_sub,
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