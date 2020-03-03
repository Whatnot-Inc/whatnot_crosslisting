import logging

import aiohttp_jinja2
import jinja2
from aiohttp import web
from aiohttp_jwt import JWTMiddleware
# from aiohttp_security import SessionIdentityPolicy
# from aiohttp_security import authorized_userid
# from aiohttp_security import setup as setup_security
# from aiohttp_session import setup as setup_session
# from aiohttp_session.redis_storage import RedisStorage
import aioredis
# from aiohttpdemo_blog.db_auth import DBAuthorizationPolicy
from .settings import load_config, PACKAGE_NAME
from .db import init_db
from .routes import setup_routes


log = logging.getLogger(__name__)


async def setup_redis(app):

    pool = await aioredis.create_redis_pool((
        app['config']['REDIS_HOST'],
        app['config']['REDIS_PORT']
    ), password=app['config']['REDIS_PWD'])

    async def close_redis(app):
        pool.close()
        await pool.wait_closed()

    app.on_cleanup.append(close_redis)
    app['redis_pool'] = pool
    return pool


async def current_user_ctx_processor(request):
    is_anonymous = True
    return {'current_user': {'is_anonymous': is_anonymous}}


async def init_app(config=None):

    app = web.Application(
        middlewares=[
            JWTMiddleware(
                config['JWT_SECRET'],
                whitelist=[
                    r'/public*',
                ]
            )
        ]
    )

    app.update(
        config=config or load_config(),
        logger=log
    )

    setup_routes(app)

    # db_pool = await init_db(app)
    app.on_startup.append(init_db)
    # app.on_startup.append(setup_redis)

    # redis_pool = await setup_redis(app)
    # setup_session(app, RedisStorage(redis_pool))

    # needs to be after session setup because of `current_user_ctx_processor`
    # aiohttp_jinja2.setup(
    #     app,
    #     loader=jinja2.PackageLoader('app/templates'),
    #     # context_processors=[current_user_ctx_processor],
    # )

    # setup_security(
    #     app,
    #     SessionIdentityPolicy(),
    #     DBAuthorizationPolicy(db_pool)
    # )

    log.debug(app['config'])

    return app


async def run(*argv):
    # print(argv)
    config = load_config()
    logging.basicConfig(level=logging.DEBUG)
    app = await init_app(config)
    return app
# server =

if __name__ == '__main__':
    app = init_app()
    web.run_app(app)
