import asyncio

import aioredis
from aiohttp import web
from settings import REDIS_HOST, REDIS_PORT, SERVER_IP, SERVER_PORT
from views import routes


async def init_app():
    app = web.Application()
    app["redis_pool"] = await aioredis.create_redis_pool((REDIS_HOST, REDIS_PORT))
    app.add_routes(routes)
    return app


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(init_app())
    web.run_app(app, host=SERVER_IP, port=SERVER_PORT)
