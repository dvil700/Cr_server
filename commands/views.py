from aiohttp import web
from aiohttp.web import json_response
import asyncio
import json
from commands import choose_command, get_already_executed
from aiojobs.aiohttp import atomic
from datetime import datetime


def make_error_json_message(data):
    if isinstance(data, str):
        return json.dumps({'errors': [data, ]})
    elif isinstance(data, list):
        return json.dumps({'errors': data})
    else:
        raise TypeError


@atomic
async def command_handler(request):
    user = request['user']
    current_command = choose_command(request.rel_url.parts[-1][:-3], user.id, request.config_dict['db'],
                                     request['data'], datetime_add=datetime.now())
    if not current_command:
        raise web.HTTPBadRequest(content_type='application/json',
                                 text=make_error_json_message('Команда не содержится в запросе, либо запрещена'))
    if not current_command.is_valid:
        raise web.HTTPBadRequest(content_type='application/json',
                                 text=make_error_json_message(current_command.get_errors()))

    # в случае если команда уже приходила, возвращаем код ответа 208 с id и location в заголовке
    # не по феншую но как-то так
    is_repeated = await current_command.check_if_repeated()
    if is_repeated:
        data = await current_command.repeated_request_represent()
        headers = {'Location': '/get_result?id=%s'%data['id']}
        return json_response(status=data['status'], headers=headers, data={'operation_id': data['id']})

    await current_command.add_new_in_db()

    # Добавляем команду в invoker
    await request.config_dict['invoker'].put(current_command)
    try:
        # ждем, пока выполнится команда EXECUTION_WAITING_TIMEOUT секунд.
        await asyncio.wait_for(current_command.wait_executed(),
                               timeout=request.config_dict['EXECUTION_WAITING_TIMEOUT'])
    except asyncio.TimeoutError:
        headers = {'Location': '/get_result?id=%s' % str(current_command.id)}
        return json_response(status=202, headers=headers, data={'id': current_command.id})
    data = current_command.represent()
    print(data)
    return json_response(status=data['status'], data=data)


async def result_handler(request):
    req_id = request['data'].get('id', None)
    if not req_id:
        raise web.HTTPNotFound()
    current_command = get_already_executed(req_id, request['user'].id, request['db'])
    data = current_command.represent()
    return json_response(status=data['status'], data=data)
