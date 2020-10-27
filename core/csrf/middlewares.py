from aiohttp import web
from aiohttp_session import get_session
from .forms import CsrfForm


@web.middleware
async def csrf_middleware(request, handler):
    session_info = await(get_session(request))
    if request.method == 'POST':
        if request.content_type == 'application/json':
            data = await request.json()
        else:
            data = await request.post()

        if not data.get('csrf_token', None):
            raise web.HTTPForbidden(text='CSRF FAILURE')
        csrf_form = CsrfForm(csrf_token=data['csrf_token'], csrf_context=session_info)
        if not csrf_form.validate():
            raise web.HTTPForbidden(text='CSRF FAILURE')
    request['csrf'] = CsrfForm(csrf_context = session_info)
    return await handler(request)
