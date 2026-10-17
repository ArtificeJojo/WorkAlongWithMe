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

CONNECTION = "postgres://tsdbadmin:nuvtsphtfx9213t1@ohkx4rugfy.jytsb7wpa9.tsdb.cloud.timescale.com:31169/tsdb?sslmode=require"

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
        await auth0().complete_interactive_login(
            request.url,
            store_options={"request": request},
        )
    except Exception as e:
        # Send the error back to index.html, which already displays ?error= params
        app.logger.warning("Login callback failed", exc_info=True)
        return redirect("/?" + urlencode({"error": "login_failed", "error_description": str(e)}))

    return redirect("/")


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



# @app.route("/home")
# def home():
#     keyID = request.cookies.get("SESSION")
#     if not keyID:
#         return redirect(url_for(""))

async def main():
    conn = await asyncpg.connect(CONNECTION)
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