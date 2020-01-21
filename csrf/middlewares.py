from aiohttp import web
from aiohttp_session import get_session
from .forms import CsrfForm


@web.middleware
async def csrf_middleware(request, handler):
    session_info = await(get_session(request))
    if request.method == 'POST':
        csrf_form = CsrfForm(await request.post(), csrf_context=session_info)
        if not csrf_form.validate():
            raise web.HTTPBadRequest()
    request['csrf'] = CsrfForm(csrf_context = session_info)
    return await handler(request)
