from aiohttp import web, BasicAuth
from aiohttp_security import authorized_userid
from aiohttp_session import get_session
from .auth import authorized_id, auth
from . import get_perm_entry
from functools import partial
import json



@web.middleware
async def ident_middleware(request, handler):
    user = await authorized_userid(request)
    if not user:
        # Если не идентифицирован, значит гость:
        user = await authorized_id(None)

    request['user'] = user
    return await handler(request)


def site_auth_middleware_factory(login_page_handler):
    @web.middleware
    async def auth_middleware(request, handler):
        if request.match_info.route.name == 'static':
            return await handler(request)
        if request['user'].is_authenticated:
            if request['user'].superuser:
                return await handler(request)
            resource = request.match_info.route.resource
            if resource:
                accepted = await _check_permission(request)
                if not accepted:
                    raise web.HTTPForbidden()
            return await handler(request)
        lph = login_page_handler
        if handler.keywords.get('handler', None) == lph:
            request['redirected_to_login'] = False
            return await handler(request)
        lph = partial(handler, handler=lph)
        request['redirected_to_login'] = True
        return await lph(request)

    return auth_middleware


def authentication_failed_response():
    return web.HTTPForbidden(content_type='application/json',
                             text=json.dumps({'errors': ['Аутентификация не пройдена', ]}))


async def _check_permission(request):
    resourse_permission = '__'.join((get_perm_entry(request.config_dict, request.path), request.method.lower()))
    user_permissions = await request['user'].get_permissions()
    return resourse_permission in user_permissions


@web.middleware
async def rest_auth_middleware(request, handler):
    if request.method == 'POST':
        try:
            data = await request.json()
            request['data'] = data
        except:
            raise authentication_failed_response()
    elif request.method == 'GET':
        auth_header = request.headers.get('AUTHORIZATION')
        if auth_header is None:
            raise authentication_failed_response()
        base_auth = BasicAuth.decode(auth_header)
        data = dict(login=base_auth.login, password=base_auth.password)
    else:
        raise web.HTTPNotImplemented

    try:
        user = await auth(data['login'], data['password'])
    except:
        raise authentication_failed_response()

    request['user'] = user
    if not user.is_authenticated:
        raise authentication_failed_response()

    resource = request.match_info.route.resource
    if resource:
        accepted = await _check_permission(request)
        if not accepted:
            raise web.HTTPForbidden(content_type='application/json',
                                    text=json.dumps(
                                        {'errors': [
                                            'У Вас нет прав доступа к ресурсу, обратитесь к администратору', ]}))

    return await handler(request)
