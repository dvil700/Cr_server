from aiohttp import web
from aiohttp.web import json_response
import asyncio
import json
from commands import choose_command
from pymysql.err import IntegrityError
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
async def command_handler(request):  # Обработчик запросов
    user = request['user']
    current_command = choose_command(user.id, request['data'], datetime_add=datetime.now())
    if not current_command:
        raise web.HTTPBadRequest(content_type='application/json',
                                 text=make_error_json_message('Команда не содержится в запросе, либо запрещена'))
    if not current_command.is_valid:
        raise web.HTTPBadRequest(content_type='application/json',
                                 text=make_error_json_message(current_command.get_errors()))

    try:
        await current_command.add_new_in_db()
    except IntegrityError:  # в случае если команда уже приходила, возвращаем код ответа 208 с id и location в заголовке
        data = await current_command.repeated_request_represent()
        headers = {'Location': '/get_result?id=' + str(data['id'])}
        return json_response(status=208, headers=headers, data=data)

    await request.config_dict['invoker'].put(current_command)
    try:
        await asyncio.wait_for(current_command.wait_executed(),
                               timeout=request.config_dict['EXECUTION_WAITING_TIMEOUT'])
    except asyncio.TimeoutError:
        headers = {'Location': '/get_result?id=' + str(current_command.id)}
        return json_response(status=202, headers=headers, data={'id': current_command.id})
    data = current_command.represent()
    print(data)
    return json_response(status=data['status'], data=data)


async def result_handler(request):
    req_id = request['data'].get('id', None)
    if not req_id:
        raise web.HTTPBadRequest(content_type='application/json',
                                 text=make_error_json_message(current_command.get_errors()))
