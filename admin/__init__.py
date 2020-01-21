from aiohttp import web
from .urls import routes
import aiohttp_jinja2
import jinja2
from aiohttp_session import session_middleware
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from aiohttp_security import SessionIdentityPolicy, setup
from auth.policies import MainAuthorizationPolicy
from auth.middlewares import ident_middleware, site_auth_middleware_factory
from admin.views import login_handler
from csrf import csrf_middleware
import pathlib
import os


def init():
    key = bytes(os.environ['SESSION_SECRET'], 'utf-8')
    middleware = session_middleware(EncryptedCookieStorage(secret_key=key, cookie_name="SSID"))
    auth_middleware = site_auth_middleware_factory(login_handler)
    app = web.Application(middlewares=[middleware, csrf_middleware, ident_middleware, auth_middleware, ])

    policy = SessionIdentityPolicy()
    setup(app, policy, MainAuthorizationPolicy())
    app.add_routes(routes)
    aiohttp_jinja2.setup(app,
                         context_processors=[aiohttp_jinja2.request_processor, ],
                         loader=jinja2.PackageLoader('admin', 'template')
                         )

    app.router.add_static('/static/', '%s\\static\\' % pathlib.Path(__file__).parent, show_index=True,
                          append_version=True, name = 'static')
    app['static_root_url'] = '/static'

    return app