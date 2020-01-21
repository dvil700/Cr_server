from aiohttp import web
from aiohttp.web import json_response
import asyncio
import ssl
import json
import commands
import auth
from commands import choose_command
import logging
import db
from config import EXECUTION_WAITING_TIMEOUT
import config
from commands.invoker import Invoker
from pymysql.err import IntegrityError
from aiojobs.aiohttp import atomic, setup
from drivers.atol10_adapter import Atl_cash_register
from auth import auth_middleware


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
    current_command = choose_command(user.id, request['data'])
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

    await Invoker().put(current_command)
    try:
        await asyncio.wait_for(current_command.wait_executed(), timeout=EXECUTION_WAITING_TIMEOUT)
    except asyncio.TimeoutError:
        headers = {'Location': '/get_result?id=' + str(current_command.id)}
        return json_response(status=202, headers=headers, data={'id': current_command.id})
    data = current_command.represent()
    return json_response(status=data['status'], data=data)


async def result_handler(request):
    req_id = request['data'].get('id', None)
    if not req_id:
        raise web.HTTPBadRequest(content_type='application/json',
                                 text=make_error_json_message(current_command.get_errors()))


def wakeup():
    loop = asyncio.get_event_loop()
    loop.call_later(1, wakeup)


def activate_logger():
    logger = logging.getLogger('main_log')
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler("/var/log/kassa10.log")
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger


if __name__ == '__main__':
    print('Запуск...')
    loop = asyncio.get_event_loop()

    #    sc = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
    #    sc.load_cert_chain('cert127.crt', 'key127.key')

    server = await loop.create_server(app.make_handler(), host='192.168.43.101', port=3080)  # , ssl=sc)

    server = loop.create_task(init(loop))
    loop.call_later(1, wakeup)

    for socket in server.sockets:
        print('Сервер запущен на {}'.format(socket.getsockname()))
    print('Выход по Ctrl+C\n')

    try:
        loop.run_forever()
    except KeyboardInterrupt:  # Окончание программы нажатием Ctrl+C
        pass
    finally:

        server.close()  # Закрываем протокол
        loop.run_until_complete(server.wait_closed())  # Асинхронно ожидаем окончания закрытия
    loop.close()  # Закрываем цикл событий
