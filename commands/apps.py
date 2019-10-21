from commands.urls import routes
from aiojobs.aiohttp import setup
from aiohttp import web
from drivers.atol10_adapter import Atl_cash_register, Tst_cr_adapter
from commands.invoker import Invoker
from commands.middlewares import auth_middleware


def init(cr_config, connection_timeout=6, test_without_hardware=False, loop=None):
    app = web.Application(loop=loop, middlewares=[auth_middleware, ])
    app.add_routes(routes)
    app['EXECUTION_WAITING_TIMEOUT'] = connection_timeout
    setup(app, close_timeout=connection_timeout)
    app.cleanup_ctx.append(make_context(cr_config, test_without_hardware))
    return app


def make_context(cr_config, test_without_hardware=False):
    async def context(app):
        if test_without_hardware:
            cash_register = Tst_cr_adapter(**cr_config, loop=app.loop)
        else:
            cash_register = Atl_cash_register(**cr_config, loop=app.loop)
        app['invoker'] = Invoker(cash_register, loop=app.loop)
        yield
        await app['invoker'].close()
        await cash_register.close()

    return context
