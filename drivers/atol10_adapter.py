from drivers import libfptr101
import asyncio
from abc import ABC, abstractmethod
import time
import random
from datetime import datetime
from .shifts import AutoShift, ManualShift
import logging


def get_logger():
    logger = logging.getLogger(__name__)
    if len(logger.handlers) > 0:
        return logger
    # если нет настроенного логера для модуля, настраиваем его
    log_handler = logging.FileHandler(__name__ + '.log')
    log_handler.formatter = logging.Formatter('%(asctime)s -  %(levelname)s - %(message)s')
    logger.addHandler(log_handler)
    return logger


async def get_cash_register(cr_model, cr_port, cr_ofd_channel, cr_baudrate, cr_protocol, cr_passwd,
                            shift_duration=86400, closing_delay=5, loop=None, test=False,
                            activation_timeout=5, shift_start_time=None):
    # Инстанциирование кассы с автоматической сменой. Если параметр test == true, то в качестве результата возвращается
    # тестовая касса (эмулятор кассы). Параметр shift_start_time - для тестовой кассы
    # activation_timeout - максимальное время за которое должна активаться смена
    auto_shift = AutoShift(shift_duration=shift_duration, closing_delay=closing_delay)
    if test:
        cr_object = TstCrAdapter(cr_model, cr_port, cr_ofd_channel, cr_baudrate, cr_protocol, cr_passwd,
                                 shift_object=auto_shift, loop=loop, activation_timeout=activation_timeout,
                                 logger=get_logger(), shift_start_time=shift_start_time)
    else:
        cr_object = AtlCashRegister(cr_model, cr_port, cr_ofd_channel, cr_baudrate, cr_protocol, cr_passwd,
                                    shift_object=auto_shift, activation_timeout=activation_timeout, logger=get_logger(),
                                    loop=loop)
    try:
        await asyncio.wait_for(cr_object.shift_init_task, activation_timeout)
    except Exception as e:
        get_logger().error(' - '.join(('Activation', type(e).__name__, str(e))))
        raise e
    return cr_object


class CROperationError(Exception):
    def __init__(self, route, data):
        self.data = data
        self.route = route


class CRFatalError(Exception):
    def __init__(self, text):
        self.text = text


class CrDataHolderABC(ABC):
    # Объекты реализаций данного абстрактного класса хрянят данные о кассе, ее серийные и регистрационные номера, данные
    # об организации и ОФД
    @abstractmethod
    def get_value_dict(self) -> dict:
        pass


class CrDataHolderFactoryABC(ABC):
    def __init__(self, dataholder_cls: type):
        self.dataholder_cls = dataholder_cls

    async def create_data_holder(self, data: dict) -> CrDataHolderABC:
        pass


def cr_coro(method):  # Декоратор для асинхронного использования методов работы с кассой (обернутые методы выполняются
    # в отдельном потоке). При исполнении метода используется блокировка, которая снимается после завершения выполнения
    # метода.
    async def wrapped(self, *args):
        async with self.lock:
            try:
                result = await self.loop.run_in_executor(None, method, self, *args)
            except Exception as e:
                # Записываем данные об ошибке в log
                if self.logger:
                    self.logger.error(' - '.join((str(method), type(e).__name__, str(e))))
                raise e
        return result

    return wrapped


class CashRegisterABC(ABC):
    # Абстрактный класс адаптера, через его интерфейс осуществляется взаимодействие программы с драйвером кассы
    def __init__(self, shift_object, name=None, activation_timeout=5, logger=None, loop=None):
        self.name = name  # Имя кассы (может понадобиться, на случай, если касс больше одной)
        self.activation_timeout = activation_timeout  # максимальное время для активации кассы
        self.logger = logger
        self.lock = asyncio.Lock()
        if not loop:
            loop = asyncio.get_event_loop()
        self.loop = loop
        self._cr_data = None  # поле, хранящее объект с рег. данными кассы, серийные номера, данные офд и предприятия
        self.shift = shift_object
        # Создадим задачу по созданию инициализации объекта смены (если смена автоматическая, то необходимо достать
        # данные о смене из кассы)
        self.shift_init_task = loop.create_task(self.shift.activate(self))

    @property
    def active(self):
        # Касса готова к работе
        return self.shift.active

    @cr_coro
    def register_operation(self, email, products, payments, total, receipttype, operator=None,
                           is_electronary=True, r1192=None):
        # Регистрация фискальной операции
        result = self._register_operation(email, products, payments, total, receipttype, operator,
                                          is_electronary, r1192)
        # В случае, если смена не была открыта до момента регистрации фискальной операции (например до момента пробития
        # чека продажи), то при ее регистрации (фискальной операции) смена открывается автоматически (по крайней
        # мере на модели кассы 30Ф)
        if self.shift.state.closed:
            # Сообщаем объекту смены, что смена в кассе открыта.
            self.shift.open()
        if self.cr_data:
            result['cr_data'] = self.cr_data.get_value_dict()

        return result

    @abstractmethod
    def _register_operation(self, email, products, payments, total, receipttype, operator,
                            is_electronary, r1192):
        # Реализация для конкретных касс регистрация фискальной операции
        pass

    @cr_coro
    @abstractmethod
    def close(self):
        # Завершение работы кассы
        pass

    @cr_coro
    def close_shift(self, delay=0):
        # Публичный метод закрытия смены.
        with self.shift.close() as closing_allowed:
            if closing_allowed:
                self._close_shift(delay)

    @abstractmethod
    def _close_shift(self, delay):
        # Метод закрытия смены. Здесь должна лежать основная логика
        pass

    @property
    def cr_data(self) -> CrDataHolderABC:
        # рег. данные кассы в налоговой, серийные номера оборудования,
        # данные о предприятии
        return self._cr_data

    @cr_coro
    @abstractmethod
    def extract_cr_data(self) -> dict:
        # Метод должен извлекать данные о серийных, рег. номерах, организации из кассового устройства и возвращать
        # в виде словаря
        pass

    @cr_coro
    def get_shift_state(self) -> dict:  # состояние смены
        # возвращает словарь с ключами ['value'] =  0 - смена закрыта, 1 - открыта, 2 - время смены истекло
        # ['number'] - номер, ['start_dateTime'] время открытия смены, ['now_dateTime'] - время в кассовом аппарате
        pass

    async def set_cr_data(self, data_holder_factory: CrDataHolderFactoryABC):
        # # метод запрашивает регистрационные и данные об оборудовании у кассы и устанавливает в свойство self._cr_data
        #  data = await self.extract_cr_data()
        data = await self.extract_cr_data()
        self._cr_data = await data_holder_factory.create_data_holder(data)


class TstCrAdapter(CashRegisterABC):
    # заглушка для тестирования
    def __init__(self, cr_model, cr_port, cr_ofd_channel, cr_baudrate, cr_protocol, cr_passwd, shift_object=None,
                 activation_timeout=5, name=None, logger=None, loop=None, shift_start_time=None):
        # shift_start_time - время открытия смены смены для тестирования (тип datetime)
        self.shift_start_time = shift_start_time
        self.doc_num = 200  # Начальный номер документа (используется только для тестов)
        self.shift_num = 200  # Начальный номер смены (используется только для тестов)
        super().__init__(shift_object, loop)

    def _close_shift(self, delay):
        # Метод закрытия смены
        time.sleep(delay)

    async def register_operation(self, email, products, payments, total, receipttype, operator=None,
                                 is_electronary=True, r1192=None):
        result = await super().register_operation(email, products, payments, total, receipttype, operator,
                                                  is_electronary, r1192)
        # shift_start_time, shift_num, doc_num переменные для тестирования. В рабобочей версии, их быть не должно
        self.shift_start_time = datetime.now()
        return result

    def _register_operation(self, email, products, payments, total, receipttype, operator,
                            is_electronary, r1192):
        # Разные операции могут выполняться разное время
        time.sleep(random.randint(0, 2))

        return {'documentNumber': self.doc_num, 'receiptType': 1, 'fiscalSign': 55566,
                'documentDate': str(datetime.now()), 'document_summ': total}

    @cr_coro
    def close(self):
        pass

    @cr_coro
    def extract_cr_data(self):
        time.sleep(0.1)
        data = dict(fns_url='https://www.nalog.ru', address='www.mysite.ru', company='ООО "МС"',
                    email='email@mysite.ru',
                    payment_addr='ул. Ленина, д.50', reg_num='2234254545335', ffd_version=105,
                    ofd_name='ООО "ОФД', ofd_inn='45353534535', inn='32423424234')
        data['serial_num'] = '4534543543543'
        data['fn_serial'] = '342342423432234'
        return data

    @cr_coro
    def get_shift_state(self):  # состояние смены
        result = {'value': 1, 'number': 222, 'start_dateTime': datetime.now(),
                  'now_dateTime': datetime.now()}
        if self.shift_start_time:
            result['start_dateTime'] = self.shift_start_time
        return result


class AtlCashRegister(CashRegisterABC):
    def __init__(self, cr_model, cr_port, cr_ofd_channel, cr_baudrate, cr_protocol, cr_passwd, shift_object=None,
                 activation_timeout=5, name=None, logger=None, loop=None):
        # cr_model - модель кассы, cr_port - тип порта, cr_ofd_channel - канал для обмена с ОФД ,
        # cr_baudrate -скорость соединения
        # cr_protocol - версия протокола обмена драйвера с кассой , cr_passwd - пароль пользователя кассы
        # указанные выше параметры, их значения описаны на сайте производителя касс, также можно ориентироваться по
        # исходному коду DTO, все константы и переменные  имеют понятные названия
        self.lock = asyncio.Lock()
        dtolib = 'drivers/libfptr10.so'
        self.driver = libfptr101.IFptr(dtolib)
        self._setsinglesetting('UserPassword', cr_passwd)
        self._setsinglesetting('LIBFPTR_SETTING_MODEL', cr_model)
        self._setsinglesetting('LIBFPTR_SETTING_PORT', cr_port)
        self._setsinglesetting('LIBFPTR_SETTING_OFD_CHANNEL', cr_ofd_channel)
        self._setsinglesetting('BaudRate', cr_baudrate)
        self._setsinglesetting('Protocol', cr_protocol)
        self.driver.applySingleSettings()
        self.driver.open()
        if not self.driver.isOpened():
            raise RuntimeError('Невозможно подключиться к кассовому аппарату')
        super().__init__(shift_object, loop)

    def _close_shift(self, delay=0):
        time.sleep(delay)
        self._setparam('LIBFPTR_PARAM_REPORT_TYPE', 'LIBFPTR_RT_CLOSE_SHIFT')
        # self._setparam('LIBFPTR_PARAM_REPORT_ELECTRONICALLY', True) #чтобы не печатался отчет о закрытии смены
        self.driver.report()
        counter = 0
        while self.driver.checkDocumentClosed() < 0:  # проверка закрыт ли документ      
            time.sleep(0.5)
            counter += 1
            if counter >= 10:
                raise CRFatalError('Невозможно закрыть смену')

    @cr_coro
    def get_shift_state(self):  # состояние смены
        data = {}
        self._setparam('LIBFPTR_PARAM_DATA_TYPE', 'LIBFPTR_DT_SHIFT_STATE')
        self._querydata()
        data['value'] = self._getparamint(
            'LIBFPTR_PARAM_SHIFT_STATE')  # 0 - смена закрыта, 1 - открыта, 2 - время смены истекло
        data['number'] = self._getparamint('LIBFPTR_PARAM_SHIFT_NUMBER')
        # Тип переменной datetime - datetime.datetime
        data['start_dateTime'] = self._getparamdatetime('LIBFPTR_PARAM_DATE_TIME')
        data['now_dateTime'] = self._get_time()
        return data

    @cr_coro
    def get_time(self):
        return self._get_time()

    @cr_coro
    def extract_cr_data(self):
        # достаем данные о регистрации, серийные номера, данные об организации из кассового аппарата
        self._setparam('LIBFPTR_PARAM_FN_DATA_TYPE', 'LIBFPTR_FNDT_REG_INFO')
        self._fnquerydata()
        getint = self._getparamint
        getstr = self._getparamstring
        data = dict(fns_url=getstr(1060), address=getstr(1009), inn=getstr(1018), company=getstr(1048),
                    payment_addr=getstr(1187), reg_num=getstr(1037), ffd_version=getint(1209),
                    ofd_name=getstr(1046), ofd_inn=getstr(1017), email=getstr(1117), )

        self._setparam('LIBFPTR_PARAM_DATA_TYPE', 'LIBFPTR_DT_STATUS')
        self._querydata()
        data['serial_num'] = getstr('LIBFPTR_PARAM_SERIAL_NUMBER')

        self._setparam('LIBFPTR_PARAM_FN_DATA_TYPE', 'LIBFPTR_FNDT_FN_INFO')
        self._fnquerydata()
        data['fn_serial'] = getstr('LIBFPTR_PARAM_SERIAL_NUMBER')
        return data

    def _get_time(self):  # текущее время в кассе
        self._setparam('LIBFPTR_PARAM_DATA_TYPE', 'LIBFPTR_DT_DATE_TIME')
        self._querydata()
        cr_dateTime = self._getparamdatetime('LIBFPTR_PARAM_DATE_TIME')
        return cr_dateTime

    def _get_const(self, param):
        # ДТО кассы содержит константы с именами в стиле LIBFPTR_PARAM_DATE_TIME, их значения используются в качестве
        # параметров в методах взаимодействия с кассой. Данный метод достает значение константы по ее имени, если
        # передано имя константы. Если передано int значение, то оно возвращается в качестве результата.
        if isinstance(param, str):
            return getattr(self.driver, param)
        elif isinstance(param, int):
            return param
        else:
            raise ValueError

    # Адаптируем методы работы с кассой под более короткую запись:
    def _getparamint(self, param):
        return self.driver.getParamInt(self._get_const(param))

    def _getparamdouble(self, param):
        return self.driver.getParamDouble(self._get_const(param))

    def _getparamstring(self, param):
        return self.driver.getParamString(self._get_const(param))

    def _getparamdatetime(self, param):
        return self.driver.getParamDateTime(self._get_const(param))

    def _getparambool(self, param):
        return self.driver.getParamDateTime(self._get_const(param))

    def _setsinglesetting(self, param, value):
        if isinstance(param, str):
            param = self._get_const(param) if param[:8] == 'LIBFPTR_' else param
        if isinstance(value, str):
            value = self._get_const(value) if value[:8] == 'LIBFPTR_' else value
        self.driver.setSingleSetting(str(param), str(value))

    def _setparam(self, param, value):
        if isinstance(param, str):
            param = self._get_const(param)
        if isinstance(value, str):
            value = self._get_const(value) if value[:8] == 'LIBFPTR_' else value
        self.driver.setParam(param, value)

    def _openreceipt(self):
        return self.driver.openReceipt()

    def _errordescription(self):
        return self.driver.errorDescription()

    def _sort_by_payment_type(self, item):
        return int(item['paymentType'])

    def _register_payments(self, payments):
        payments.sort(key=self._sort_by_payment_type, reverse=True)
        for payment in payments:
            self._setparam('LIBFPTR_PARAM_PAYMENT_TYPE', payment['paymentType'])
            self._setparam('LIBFPTR_PARAM_PAYMENT_SUM', float(payment['summ']))
            if self.driver.payment() < 0:
                self._cancel_receipt()
                raise CROperationError(self.name, 'Ошибка регистрации оплаты: ' + self._errordescription())
        # Тип оплаты LIBFPTR_PARAM_PAYMENT_TYPE
        # 0 - наличными
        # 1 - безналичными
        # 2 - предварительная оплата (аванс)
        # 3 - последующая оплата (кредит)

    def _register_products(self, products):
        for product in products:
            self._setparam('LIBFPTR_PARAM_COMMODITY_NAME', product['name'])
            self._setparam('LIBFPTR_PARAM_PRICE', float(product['price']))
            self._setparam('LIBFPTR_PARAM_QUANTITY', int(product['quantity']))
            self._setparam('LIBFPTR_PARAM_TAX_TYPE',
                           'LIBFPTR_TAX_NO')  # налог. Если организация платит НДС, то необходимо изменить с этим учетом
            self._setparam(1212, int(product['paymentObject']))
            if self.driver.registration() < 0:
                self._cancel_receipt()
                raise CROperationError(self.name, 'Ошибка регистрации товара: ' + self._errordescription())

    def _querydata(self):
        self.driver.queryData()

    def _fnquerydata(self):
        self.driver.fnQueryData()

    def _set_operator(self, operator):  # при оффлайн продаже необходимо указать оператора
        self._setparam(1021, operator['name'])
        self._setparam(1203, operator['inn'])
        if self.driver.operatorLogin() < 0:
            raise CROperationError(self.name, 'Не удалось добавить оператора')

    def _cancel_receipt(self):
        self.driver.cancelReceipt()

    @cr_coro
    def cancel_receipt(self):
        self.driver.cancelReceipt()

    @cr_coro
    def get_not_sent_docs(self):
        # Вернуть данные о неотправленных документах
        self._setparam('LIBFPTR_PARAM_FN_DATA_TYPE', 'LIBFPTR_FNDT_OFD_EXCHANGE_STATUS')
        self._fnquerydata()
        data = dict()
        data['unsentCount'] = self._getparamint('LIBFPTR_PARAM_DOCUMENTS_COUNT')
        data['unsentFirstNumber'] = self._getparamint('LIBFPTR_PARAM_DOCUMENT_NUMBER')
        data['unsentDateTime'] = self._getparamdatetime('LIBFPTR_PARAM_DATE_TIME')
        return data

    @cr_coro
    def print_ofd_connection_report(self):
        # Печать отчета о соединении с ОФД
        self._setparam('LIBFPTR_PARAM_REPORT_TYPE', 'LIBFPTR_RT_OFD_TEST')
        self.driver.report()

    @cr_coro
    def show_ofd_connection_report(self, command):
        # Возвращает данные о соединении с ОФД
        result = command.result
        self._setparam('LIBFPTR_PARAM_FN_DATA_TYPE', 'LIBFPTR_FNDT_OFD_EXCHANGE_STATUS')
        self._fnquerydata()
        result['exchangeStatus'] = self._getparamint('LIBFPTR_PARAM_OFD_EXCHANGE_STATUS')  # статус инф. обмена
        result['unsentCount'] = self._getparamint('LIBFPTR_PARAM_DOCUMENTS_COUNT')  # Кол. неотправленных документов
        result['firstUnsentNumber'] = self._getparamint('LIBFPTR_PARAM_DOCUMENT_NUMBER')  # Номер первого из
        # неотправленных документов
        result['ofdMessageRead'] = self._getparambool(
            'LIBFPTR_PARAM_OFD_MESSAGE_READ')  # Флаг наличия сообщения для ОФД
        result['dateTime'] = self._getparamdatetime('LIBFPTR_PARAM_DATE_TIME')
        return result

    def _register_operation(self, email, products, payments, total, receipttype, operator=None,
                            is_electronary=True, r1192=None, test_mode=False):
        # регистрация фискальной операции
        # Допустимые типы фискальных документов
        allowed_receipttypes = {1: 'LIBFPTR_RT_SELL', 2: 'LIBFPTR_RT_SELL_RETURN', 7: 'LIBFPTR_RT_SELL_CORRECTION',
                                8: 'LIBFPTR_RT_SELL_RETURN_CORRECTION', 4: 'LIBFPTR_RT_BUY', 5: 'LIBFPTR_RT_BUY_RETURN',
                                9: 'LIBFPTR_RT_BUY_CORRECTION', 10: 'LIBFPTR_RT_BUY_RETURN_CORRECTION'}
        # LIBFPTR_RT_SELL - чек прихода
        # LIBFPTR_RT_SELL_RETURN - чек возврата прихода
        # LIBFPTR_RT_SELL_CORRECTION - чек коррекции прихода
        # LIBFPTR_RT_BUY - чек расхода
        # LIBFPTR_RT_BUY_RETURN - чек возврата расхода
        # LIBFPTR_RT_BUY_CORRECTION - чек коррекции расхода
        # При регистрации возвратов и коррекции ошибок в чеках, можно руководствоваться материалами
        # https://www.nalog.ru/rn27/news/smi/7746012/
        # http://consultantkhv.ru/newspaper/ispravlenie-oshibok-dopushhennyx-pri-formirovanii-kassovyx-chekov/

        if self.driver.checkDocumentClosed() < 0:
            self.cancel_receipt()
            if self.driver.checkDocumentClosed() < 0:
                raise CROperationError(self.name, 'Предыдущий документ не закрыт или касса недоступна')

        if not is_electronary:  # чек электронный или бумажный
            self._set_operator(operator)
            self._setparam('LIBFPTR_PARAM_RECEIPT_ELECTRONICALLY', False)
        else:
            self._setparam('LIBFPTR_PARAM_RECEIPT_ELECTRONICALLY', True)

        receipttype = allowed_receipttypes[int(receipttype)]
        self._setparam('LIBFPTR_PARAM_RECEIPT_TYPE', receipttype)
        self._setparam(1008, email)

        # дополнительный реквизит 1192 рекомендуется использовать в операциях исправления ошибок:
        # возвраты, коррекции, "повторные чеки", в нем указывается ФПД исправляемого (первоначального) чека,
        # ссылка с подробной информацией о возвратах и коррекциях выше
        if r1192:
            self._setparam(1192, r1192)

        if self._openreceipt() < 0:
            self.driver.cancelReceipt()
            raise CROperationError(self.name, 'Ошибка открытия чека: ' + self._errordescription())

        try:
            # регистрируем товары и платежи
            self._register_products(products)
            self._register_payments(payments)
        except Exception as e:
            self.driver.cancelReceipt()
            raise e

        # (Налоги - НДС)
        self._setparam('LIBFPTR_PARAM_TAX_TYPE', 'LIBFPTR_TAX_NO')
        self._setparam('LIBFPTR_PARAM_TAX_SUM',
                       0)  # Если организация платит НДС, необходимо учесть это и включить налог во входные данные
        self.driver.receiptTax()
        # регистрируем итог
        self._setparam('LIBFPTR_PARAM_SUM', float(total))

        if self.driver.receiptTotal() < 0:
            self.driver.cancelReceipt()
            raise CROperationError(self.name, 'Ошибка регистрации общей суммы чека: ' + self._errordescription())

        if test_mode:
            # Если тестовый режим, то откатываем документ
            return self.driver.cancelReceipt()

        # закрываем чек
        if self.driver.closeReceipt() < 0:
            self.driver.cancelReceipt()
            raise CROperationError(self.name, 'Ошибка закрытия чека: ' + self._errordescription())

        self._setparam('LIBFPTR_PARAM_FN_DATA_TYPE', 'LIBFPTR_FNDT_LAST_RECEIPT')
        self._fnquerydata()
        return {'documentNumber': self._getparamint('LIBFPTR_PARAM_DOCUMENT_NUMBER'),
                'receiptType': self._getparamint('LIBFPTR_PARAM_RECEIPT_TYPE'),
                'document_summ': self._getparamdouble('LIBFPTR_PARAM_RECEIPT_SUM'),
                'fiscalSign': self._getparamstring('LIBFPTR_PARAM_FISCAL_SIGN'),
                'documentDate': str(self._getparamdatetime('LIBFPTR_PARAM_DATE_TIME'))}


    @cr_coro
    def close(self):
        self.driver.close()
        if self.shift.closing_task:
            self.shift.closing_task.cancell()
