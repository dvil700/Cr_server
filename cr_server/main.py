import commands
import asyncio
import os
import ssl
import admin
from auth import register_route_permissions
from aiohttp import web
import config
from db import SADataBase
from db.model import Base
from dotenv import load_dotenv
from pathlib import Path
from datetime import timedelta
from datetime import datetime

def wakeup(loop):
    loop.call_later(1, wakeup, loop)


async def context(app):
    # Контекст для основного приложения
    Base.metadata.bind = app['db']
    yield
    await app['db'].close()


async def cr_app_context(cr_app):
    # Контекст для приложения кассы Регистрируем в базе разрешения, для управления доступом к ресурсам приложения (
    # включая ресурсы вложенных приложений)
    await register_route_permissions(cr_app)
    yield


def init_app(loop, name):
    db = loop.run_until_complete(SADataBase.connect(config.DB_CONFIG, config.DB_CHARSET, loop))
    app = web.Application()
    app['db'] = db
    app.cleanup_ctx.append(context)
    cr_app = web.Application()
    shift_start_time = datetime.now()-timedelta(minutes=5)
    commands_app = commands.init(db, cr_config=config.CR_CONFIG,
                                 connection_timeout=config.COMMANDS_CONFIG['EXECUTION_WAITING_TIMEOUT'],
                                 test_without_hardware=True, shift_start_time=shift_start_time, loop=loop)

    cr_app.add_subapp('/cr_proccessing/', commands_app)
    app_admin = admin.init()
    cr_app.add_subapp('/admin/', app_admin)
    cr_app.cleanup_ctx.append(cr_app_context)
    # орпределяем корневой url до приложения кассы и его имя, они будут использоваться при фиксировании разрешений
    # на доступ к ресурсам в базе данных (чтобы не было зависимости от корневого url, который может меняться)
    cr_app['cr_app_name'] = 'cr2'
    cr_app['cr_app_prefix'] = '/cr2/'
    app.add_subapp(cr_app['cr_app_prefix'], cr_app)
    return app


async def start_app(runner, *args, **kwargs):
    await runner.setup()
    site = web.TCPSite(runner, *args, **kwargs)
    await site.start()


def main():
    # загружаем переменные окружения
    env_path = Path('.') / 'settings.env'
    if not os.path.exists(env_path):
        raise FileExistsError('Не найден файл конфигурации settings.env')
    load_dotenv(dotenv_path=env_path)

    print('Запуск...')
    loop = asyncio.get_event_loop()
    loop.call_later(1, wakeup, loop)
    app = init_app(loop, name='cr2')
    # path = os.getcwd()
    # sc = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
    # sc.load_cert_chain('%s/cert/cert.pem'%path, '%s/cert/key.pem'%path)
    runner = web.AppRunner(app)
    runner = loop.run_until_complete(start_app(runner, 'localhost', 3080))
    try:
        loop.run_forever()
    except KeyboardInterrupt:  # Окончание программы нажатием Ctrl+C
        pass
    finally:
        loop.run_until_complete(runner.cleanup())
        print('closing')

    loop.close()  # Закрываем цикл событий
    print('closed')


if __name__ == '__main__':
    main()
