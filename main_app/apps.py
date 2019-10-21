from aiohttp import web
import config
import db


def init(loop=None):
    app=web.Application()
    app.cleanup_ctx.append(context)
    return app

async def context(app):
    app['db']=await db.Data_base.connect(config.DB_CONFIG, app.loop)
    yield
    await app['db'].close()
