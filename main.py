import main_app.apps
import commands.apps
import asyncio
import config
from aiohttp import web


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
    app = main_app.apps.init(loop)
    commands_app = commands.apps.init(cr_config=config.CR_CONFIG,
                                      connection_timeout=config.COMMANDS_CONFIG['EXECUTION_WAITING_TIMEOUT'],
                                      test_without_hardware=True, loop=loop)
    app.add_subapp('/cr_proccessing/', commands_app)
    #    sc = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
    #    sc.load_cert_chain('cert127.crt', 'key127.key')

    runner = web.AppRunner(app)
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, 'localhost', 3080)


    #coro = loop.create_server(app.make_handler(), host='127.0.0.1', port=3080)  # , ssl=sc)

    loop.call_later(1, wakeup)
    loop.run_until_complete(site.start())
    print('Сервер запущен')

    try:
        loop.run_forever()
    except KeyboardInterrupt:  # Окончание программы нажатием Ctrl+C
        pass
    finally:
        print('closing')
        loop.run_until_complete(runner.cleanup())
    loop.close()  # Закрываем цикл событий
    print('closed')
