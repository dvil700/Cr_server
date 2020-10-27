import datetime
import logging
import time
from receipt import Receipt, Cashier, ReceiptRegistratorData, Commodity, Payment
from hardware.adapters.base import AbstractRegistratorDriverAdapter, ShiftInformation, AbstractTimeCounter
from ..exceptions import FiscalDeviceOperationError, FiscalDeviceUnavailable


logger = logging.getLogger(__name__)


class AtlCashRegister(AbstractRegistratorDriverAdapter):
    _allowed_tax_types = {1: 'LIBFPTR_TT_OSN', 2: 'LIBFPTR_TT_USN_INCOME', 4: 'LIBFPTR_TT_USN_INCOME_OUTCOME',
                          8: 'LIBFPTR_TT_ENVD', 16: 'LIBFPTR_TT_ESN', 32: 'LIBFPTR_TT_PATENT'}
    # Допустимые значения в свойстве применяемой налоговой системы self._allowed_tax_types
    # LIBFPTR_TT_OSN = 1
    # LIBFPTR_TT_USN_INCOME = 2
    # LIBFPTR_TT_USN_INCOME_OUTCOME = 4
    # LIBFPTR_TT_ENVD = 8
    # LIBFPTR_TT_ESN = 16
    # LIBFPTR_TT_PATENT = 32

    _allowed_receipttypes = {1: 'LIBFPTR_RT_SELL', 2: 'LIBFPTR_RT_SELL_RETURN', 7: 'LIBFPTR_RT_SELL_CORRECTION',
                             8: 'LIBFPTR_RT_SELL_RETURN_CORRECTION', 4: 'LIBFPTR_RT_BUY', 5: 'LIBFPTR_RT_BUY_RETURN',
                             9: 'LIBFPTR_RT_BUY_CORRECTION', 10: 'LIBFPTR_RT_BUY_RETURN_CORRECTION'}

    # Допустимые типы фискальных документов в свойстве self._allowed_receipttypes
    # LIBFPTR_RT_SELL - чек прихода
    # LIBFPTR_RT_SELL_RETURN - чек возврата прихода
    # LIBFPTR_RT_SELL_CORRECTION - чек коррекции прихода
    # LIBFPTR_RT_BUY - чек расхода
    # LIBFPTR_RT_BUY_RETURN - чек возврата расхода
    # LIBFPTR_RT_BUY_CORRECTION - чек коррекции расхода

    def __init__(self, driver_object, time_counter: AbstractTimeCounter, test_mode=False):
        self.driver = driver_object
        self._time_counter = time_counter
        self._test_mode = test_mode
        if not self.driver.isOpened():
            logger.error('Unable to connect to the fiscal device %s', self)
            raise RuntimeError('Невозможно подключиться к кассовому аппарату')
        self._id = None

    def open_shift(self):
        self.driver.openShift()
        self.driver.checkDocumentClosed()

    def close_shift(self, electronary=True):
        self._setparam('LIBFPTR_PARAM_REPORT_TYPE', 'LIBFPTR_RT_CLOSE_SHIFT')
        if electronary:  # Если True, то не печатать отчет о закрытии смены
            self._setparam('LIBFPTR_PARAM_REPORT_ELECTRONICALLY', True)
        self.driver.report()
        counter = 0
        while self.driver.checkDocumentClosed() < 0:  # проверка закрыт ли документ      
            time.sleep(0.5)
            counter += 1
            if counter >= 10:
                logger.error('Unable to close the shift %s', self)
                raise FiscalDeviceOperationError('Невозможно закрыть смену')

    def get_shift_info(self) -> ShiftInformation:
        self._setparam('LIBFPTR_PARAM_DATA_TYPE', 'LIBFPTR_DT_SHIFT_STATE')
        self._querydata()
        is_open = bool(self._getparamint('LIBFPTR_PARAM_SHIFT_STATE'))
        number = self._getparamint('LIBFPTR_PARAM_SHIFT_NUMBER')
        expiration_date_time = self._getparamdatetime('LIBFPTR_PARAM_DATE_TIME')  # дата время истечения смены
        now_date_time = self.get_date_time()
        start_date_time = None
        if is_open:
            start_date_time = expiration_date_time - datetime.timedelta(hours=24)
        time_counter_value = self._time_counter.get_time_value()

        return ShiftInformation(is_open, now_date_time, self._time_counter, time_counter_value, number, start_date_time,
                                datetime_closed=None)

    def get_date_time(self):  # текущее время в кассе
        self._setparam('LIBFPTR_PARAM_DATA_TYPE', 'LIBFPTR_DT_DATE_TIME')
        self._querydata()
        cr_dateTime = self._getparamdatetime('LIBFPTR_PARAM_DATE_TIME')
        return cr_dateTime

    def set_date_time(self, dt):
        self.close_shift()
        self._setparam('LIBFPTR_PARAM_DATE_TIME', datetime.datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute,
                                                                    dt.second))
        self.driver.writeDateTime()

    def get_registrator_info(self) -> ReceiptRegistratorData:
        # достаем данные о регистрации, серийные номера, данные об организации из кассового аппарата
        self._setparam('LIBFPTR_PARAM_FN_DATA_TYPE', 'LIBFPTR_FNDT_REG_INFO')
        self._fnquerydata()
        getint = self._getparamint
        getstr = self._getparamstring
        registration_number = getstr(1037)
        ffd_version = getint(1209)
        ffd_inn = getstr(1017)
        ofd_name = getstr(1046)
        company_inn = getstr(1018)
        company_name = getstr(1048)
        operations_place = getstr(1187)
        operations_address = getstr(1009)

        self._setparam('LIBFPTR_PARAM_DATA_TYPE', 'LIBFPTR_DT_STATUS')
        self._querydata()
        registrator_serial = getstr('LIBFPTR_PARAM_SERIAL_NUMBER')

        self._setparam('LIBFPTR_PARAM_FN_DATA_TYPE', 'LIBFPTR_FNDT_FN_INFO')
        self._fnquerydata()
        fn_serial = getstr('LIBFPTR_PARAM_SERIAL_NUMBER')

        return ReceiptRegistratorData(registration_number, registrator_serial, fn_serial, ffd_version, ofd_name,
                                      ffd_inn, company_name, company_inn, operations_address, operations_place)

    def register_receipt(self, receipt: Receipt):
        try:
            self._register_receipt(receipt)
        except FiscalDeviceOperationError as e:
            logger.error('{} {} receipt_id = '.format(str(e), self, receipt.id))
            raise e

    def _register_receipt(self, receipt: Receipt):
        if not self.driver.isOpened():

            raise FiscalDeviceOperationError('Касса недоступна')

        if self.driver.checkDocumentClosed() < 0:
            self.cancel_receipt()

        if not receipt.need_print:  # печатать ли бумажный чек
            self._setparam('LIBFPTR_PARAM_RECEIPT_ELECTRONICALLY', True)

        self._set_operator(receipt.cashier)
        # Установка типа чека
        self._set_receipt_type(receipt)
        # Телефон-email
        phone_email = str(receipt.email) if receipt.email else str(receipt.phone_number)
        self._setparam(1008, phone_email)

        # Реквизит 1192 "исправляющего" чека
        if receipt.mistaken_receipt_number:
            self._setparam(1192, str(receipt.mistaken_receipt_number))
        # устанавливаем реквизиты корректирующего чека
        self._set_correction_data(receipt)
        self._set_receipt_tax_system(receipt)
        # Команда кассовому аппарату на открытие чека
        self._openreceipt()
        # Регистрируем товары и платежи
        for product in receipt.commodities:
           self._register_product(product)
        for payment in receipt.payments:
            self._register_payment(payment)
        # (Налоги - НДС)

        # self._setparam('LIBFPTR_PARAM_TAX_TYPE', 'LIBFPTR_TAX_NO')
        # self._setparam('LIBFPTR_PARAM_TAX_SUM',   0)
        # self.driver.receiptTax()

        # Регистрируем итог
        self._setparam('LIBFPTR_PARAM_SUM', float(receipt.get_commodities_total_cost()))

        if self.driver.receiptTotal() < 0:
            self.driver.cancelReceipt()
            raise FiscalDeviceOperationError('Ошибка регистрации общей суммы чека: ' + self._errordescription())

        if self._test_mode:
            # Если тестовый режим, то откатываем документ
            return self.driver.cancelReceipt()
        # закрываем чек
        self._close_receipt()
        # Достаем фискальные данные из кассы и переносим их в объект чека
        self._set_receipt_fiscal_data(receipt)

    def _set_receipt_type(self, receipt):
        try:
            receipttype = self._allowed_receipttypes[receipt.get_type_int()]
        except KeyError:
            self.cancel_receipt()
            raise FiscalDeviceOperationError('Недопустимый тип чека')
        self._setparam('LIBFPTR_PARAM_RECEIPT_TYPE', receipttype)

    def _set_correction_data(self, receipt: Receipt):
        if not receipt.is_correcting():
            return
        self._setparam(1177, str(receipt.correction_data.correction_reason))
        # Реквизит 1174 генерируется кассой из реквизитов 1178 и 1179, и потом передается в кассу параметром
        self._setparam(1178, receipt.correction_data.correction_date)
        self._setparam(1179, str(receipt.correction_data.correction_doc_number))
        self.driver.utilFormTlv()
        correction_info_1174 = self._get_param_byte_array('LIBFPTR_PARAM_TAG_VALUE')
        self._setparam('LIBFPTR_PARAM_RECEIPT_TYPE', 'LIBFPTR_RT_SELL_CORRECTION')
        self._setparam(1174, correction_info_1174)
        # Коррекция по предписанию или добровольно (0 либо 1)
        self._setparam(1173, int(receipt.correction_data.precept))

    def _set_operator(self, cashier: Cashier):  # при оффлайн продаже необходимо указать оператора
        if not cashier:
            return
        self._setparam(1021, cashier.name)
        self._setparam(1203, cashier.inn)
        if self.driver.operatorLogin() < 0:
            logger.error('{} {} receipt_id = '.format(str(e), self, receipt.id))
            raise FiscalDeviceOperationError('Не удалось добавить оператора')

    def _set_receipt_tax_system(self, receipt):
        # Система налогообложения (общая, усн расход, усн доход и т.д.)
        if not receipt.tax_system:
            return
        if receipt.tax_system.get_value_int() not in self._allowed_tax_types:
            raise FiscalDeviceOperationError('Недопустимое значение типа применяемой налоговой системы')
        self._setparam(1055, receipt.tax_system.get_value_int())

    def _register_payment(self, payment: Payment):
        self._setparam('LIBFPTR_PARAM_PAYMENT_TYPE', payment.get_type_int())
        self._setparam('LIBFPTR_PARAM_PAYMENT_SUM', float(payment.get_value()))
        if self.driver.payment() < 0:
            self.cancel_receipt()
            raise FiscalDeviceOperationError('Ошибка регистрации оплаты: {}'.format(self._errordescription()))

    # Тип оплаты LIBFPTR_PARAM_PAYMENT_TYPE
    # 0 - наличными
    # 1 - безналичными
    # 2 - предварительная оплата (аванс)
    # 3 - последующая оплата (кредит)

    def _register_product(self, product: Commodity):
        self._setparam('LIBFPTR_PARAM_COMMODITY_NAME', product.name.get_value())
        self._setparam('LIBFPTR_PARAM_PRICE', float(product.price.get_value()))
        self._setparam('LIBFPTR_PARAM_QUANTITY', float(product.quantity.get_value()))
        if not product.tax_type:
            # Если НДС не определен, то указываем
            self._setparam('LIBFPTR_PARAM_TAX_TYPE', 'LIBFPTR_TAX_NO')
        else:
            self._setparam('LIBFPTR_PARAM_TAX_TYPE', product.tax_type.get_value_int())
        self._setparam('LIBFPTR_PARAM_TAX_SUM', 0)  # сумма налога расчитывается автоматически
        self._setparam(1212, product.get_type_int())
        self._setparam(1214, product.payment_state.get_value())
        if self.driver.registration() < 0:
            self.cancel_receipt()
            raise FiscalDeviceOperationError('Ошибка регистрации товара: {}'.format(self._errordescription()))

    def _set_receipt_fiscal_data(self, receipt):
        # Достаем результаты из кассового аппарата
        self._setparam('LIBFPTR_PARAM_FN_DATA_TYPE', 'LIBFPTR_FNDT_LAST_RECEIPT')
        self._fnquerydata()

        fiscal_sign = self._getparamstring('LIBFPTR_PARAM_FISCAL_SIGN')
        receipt_number = self._getparamint('LIBFPTR_PARAM_DOCUMENT_NUMBER')
        receipt_datetime = self._getparamdatetime('LIBFPTR_PARAM_DATE_TIME')

        self._setparam('LIBFPTR_PARAM_FN_DATA_TYPE', 'LIBFPTR_FNDT_SHIFT')
        self._fnquerydata()

        receipt_in_shift_num = self._getparamint('LIBFPTR_PARAM_RECEIPT_NUMBER')
        shift_num = self._getparamint('LIBFPTR_PARAM_SHIFT_NUMBER')

        receipt.set_fiscal_data(fiscal_sign, receipt_datetime, self._id, shift_num, receipt_in_shift_num,
                                receipt_number)

    def cancel_receipt(self):
        self.driver.cancelReceipt()

    def close(self):
        self.driver.close()

    def reboot(self):
        self.driver.deviceReboot()

    ############################################################################
    # Адаптируем методы работы с кассовым драйвером под более короткую запись:##
    ############################################################################
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

    def _get_param_byte_array(self, param):
        return self.driver.getParamByteArray(self._get_const(param))

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
        result = self.driver.openReceipt()
        if result < 0:
            self.driver.cancelReceipt()
            raise FiscalDeviceOperationError('Ошибка открытия чека: ' + self._errordescription())
        return result

    def _close_receipt(self):
        result = self.driver.closeReceipt()
        if result < 0:
            self.driver.cancelReceipt()
            raise FiscalDeviceOperationError('Ошибка закрытия чека: ' + self._errordescription())
        return result

    def _errordescription(self):
        return self.driver.errorDescription()

    def _querydata(self):
        self.driver.queryData()

    def _fnquerydata(self):
        self.driver.fnQueryData()
