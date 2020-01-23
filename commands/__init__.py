from commands.commands import choose_command, get_already_executed
from commands import models
from aiojobs.aiohttp import setup
from aiohttp import web
from drivers.atol10_adapter import get_cash_register, CrDataHolderFactoryABC, CrDataHolderABC
from .invoker import Invoker
from auth.middlewares import rest_auth_middleware
from .urls import make_command_routes
from .models import CashRegister, Company, Ofd, OnlineCR, CrHardware

__all__ = ['choose_command', 'models', 'get_already_executed', 'init']


def init(db, cr_config, connection_timeout=6, test_without_hardware=False, loop=None, shift_start_time=None):
    # инициализация приложения комманд
    app = web.Application(loop=loop, middlewares=[rest_auth_middleware, ])
    app.add_routes(make_command_routes())
    app['EXECUTION_WAITING_TIMEOUT'] = connection_timeout
    setup(app, close_timeout=connection_timeout)
    app.cleanup_ctx.append(make_context(db, cr_config, test_without_hardware, shift_start_time))
    return app


class CrDataHolder(CrDataHolderABC):
    __slots__ = ('cr_hardware', 'company', 'ofd', 'cash_register', 'online_cr')

    def __init__(self, cr_hardware: CrHardware, company: Company, ofd: Ofd, cash_register: CashRegister,
                 online_cr: OnlineCR):
        self.cr_hardware = cr_hardware
        self.company = company
        self.ofd = ofd
        self.cash_register = cash_register
        self.online_cr = online_cr
        self._cache = {}

    def get_value_dict(self):
        if len(self._cache) > 0:
            return self._cache
        result = {}
        for attr_name in self.__slots__:
            attr = getattr(self, attr_name).get_value_dict()
            for key, item in attr.items():
                if 'id' in key:
                    continue
                if ('name' in result) or ('address' in result):
                    key = '%s_%s' % ((attr_name, key))
                result[key] = item
        result['online_cr_id'] = self.online_cr.id
        self._cache = result
        return result


class CrDataHolderFactory(CrDataHolderFactoryABC):
    def __init__(self, data_holder_cls, conn):
        super().__init__(data_holder_cls)
        self.conn = conn

    async def create_data_holder(self, data: dict) -> CrDataHolder:
        # регистрируем в базе и возвращяем в качестве результата данные кассы, фискального накопителя, информацию
        # об организации и офд
        conn = self.conn
        result = dict(cr_hardware=await CrHardware.register_and_get(conn, registration_number=data['reg_num'],
                                                                    serial_number=data['serial_num']),
                      company=await Company.register_and_get(conn, name=data['company'], inn=data['inn'],
                                                             address=data['address'], email=data['email'],
                                                             payment_addr=data['payment_addr']),
                      ofd=await Ofd.register_and_get(conn, name=data['ofd_name'], inn=data['ofd_inn'],
                                                     url=data.get('url', '')))

        result['cash_register'] = await CashRegister.register_and_get(conn, fn_serial=data['fn_serial'],
                                                                      cr_hardware_id=result['cr_hardware'].id)
        result['online_cr'] = await OnlineCR.register_and_get(conn, company_id=result['company'].id,
                                                              ofd_id=result['ofd'].id,
                                                              ffd_version=str(data['ffd_version'] / 100),
                                                              cash_register_id=result['cash_register'].id)

        return self.dataholder_cls(**result)


def make_context(db, cr_config, test_without_hardware=False, shift_start_time=None):
    async def context(app):
        cr_adapter = await get_cash_register(**cr_config, loop=app.loop,  test=test_without_hardware,
                                             activation_timeout=5, shift_start_time=shift_start_time)
        async with db.conn as conn:
            transaction = await conn.begin()
            try:
                await cr_adapter.set_cr_data(CrDataHolderFactory(CrDataHolder, conn))
            except Exception as e:
                await transaction.rollback()
                raise e
            await transaction.commit()

        app['invoker'] = Invoker(cr_adapter, loop=app.loop)
        yield
        await app['invoker'].close()
        await cr_adapter.close()

    return context