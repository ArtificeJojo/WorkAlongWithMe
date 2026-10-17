import asyncpg
from dotenv import load_dotenv
from os import environ as env

from auth0_server_python.auth_server.server_client import ServerClient
from auth0_server_python.auth_types import LogoutOptions, StartInteractiveLoginOptions, StateData, TransactionData
from auth0_server_python.store.abstract import AbstractDataStore

from flask import Flask, request, redirect, url_for, render_template, after_this_request
import asyncio
from markupsafe import escape
from urllib.parse import urlencode

load_dotenv()
app = Flask(__name__)


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
        first_login = await register_user(result["state_data"]["user"])
    except Exception as e:
        # Send the error back to index.html, which already displays ?error= params
        app.logger.warning("Login callback failed", exc_info=True)
        return redirect("/?" + urlencode({"error": "login_failed", "error_description": str(e)}))

    return redirect("/aboutyou" if first_login else "/home")


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
    if not await auth0().get_user(store_options={"request": request}):
        return redirect("/")

    with open("..\\src\\home.html") as html:

        return html.read()

@app.route("/aboutyou")
async def about_you():
    if not await auth0().get_user(store_options={"request": request}):
        return redirect("/")

    with open("..\\src\\about_you.html") as html:

        return html.read()

async def register_user(user):
    """Create a users row for this Auth0 account if there isn't one yet.
    Returns True when the row was just created, i.e. this is their first login."""
    display_name = user.get("name") or user.get("nickname") or user.get("email") or user["sub"]

    conn = await asyncpg.connect(env.get("DATABASE_URL"))
    try:
        new_id = await conn.fetchval(
            "INSERT INTO users (display_name, auth0_sub) VALUES ($1, $2) "
            "ON CONFLICT (auth0_sub) DO NOTHING RETURNING id",
            display_name, user["sub"],
        )
    finally:
        await conn.close()

    return new_id is not None

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