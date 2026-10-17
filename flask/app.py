import asyncpg
from flask import Flask
import asyncio

CONNECTION = "postgres://tsdbadmin:nuvtsphtfx9213t1@ohkx4rugfy.jytsb7wpa9.tsdb.cloud.timescale.com:31169/tsdb?sslmode=require"

app = Flask(__name__)

app.run()

@app.route("/")
def start():
    asyncio.run(main())
    
    return "True"

async def main():
    conn = await asyncpg.connect(CONNECTION)
    extensions = await conn.fetch("select current_date")
    for extension in extensions:
        print(extension)
    await conn.close()




# if __name__ == "__main__":
#     asyncio.run(main())