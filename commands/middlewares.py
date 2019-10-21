from aiohttp import web
import auth
import json


def authentication_failed_request():
    raise web.HTTPForbidden(content_type='application/json',
                            text=json.dumps({'errors': ['Аутентификация не пройдена', ]}))


@web.middleware
async def auth_middleware(request, handler):
    if request.method == 'POST':
        try:
            data = await request.json()
            request['data']=data
        except:
            authentication_failed_request()
    elif request.method == 'GET':
        auth_header = request.headers.get('AUTHORIZATION')
        if auth_header is None:
            authentication_failed_request()
        data = dict(zip(('username', 'passwd'), auth_header.split(':')))
    else:
        return
    try:
        user = await auth.auth(data['username'], data['passwd'])
    except:
        authentication_failed_request()

    if not user.is_authenticated:
        authentication_failed_request()
    request['user'] = user
    return await handler(request)
