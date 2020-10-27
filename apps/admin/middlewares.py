from aiohttp import web
from aiohttp_security import authorized_userid, permits
from aiohttp_jinja2 import render_template
from .forms import LoginForm


@web.middleware
async def auth_middleware(request, handler):
    if request.match_info.route.name == 'static':
        return await handler(request)
    user = await authorized_userid(request)
    if not user:
        if request.rel_url == request.app.router['login'].url_for():
            return await handler(request)
        return render_template('login.html', request, context={'form': LoginForm(), 'message': None}, status=401)
    request['user'] = user
    strategy = request.app['admin_access_attr_calc_strategy']

    if not await permits(request, strategy.get_resource_id(request), context=strategy.get_context(request)):
        raise web.HTTPForbidden
    return await handler(request)

