from hardware.adapters.base import AbstractRegistratorDriverAdapter, ShiftInformation, DefaultTimeCounter
from receipt import ReceiptRegistratorData
from time import sleep
import datetime
import random
from logging import getLogger


logger = getLogger(__name__)


class TestRegistrator(AbstractRegistratorDriverAdapter):
    _registrator_info = ReceiptRegistratorData(registration_number='002353466533',
                                               registrator_serial='2356547774453454', fn_serial='0023423423',
                                               ffd_version='105', ofd_name='ООО "ОФД"', ffd_inn='34567789999',
                                               company_name='ИП Иванов Иван Иванович', company_inn='664353523234',
                                               operations_address='Ленина 55, Москва',
                                               operations_place='http://www.sale.ru')

    def __init__(self):
        self._shift_is_open = False
        self._shift_number = 10
        self._shift_documents_count = 0
        self._shift_datetime_open = None
        self._time_counter = DefaultTimeCounter()
        self._receipt_num = 0
        # Метки времени в datetime и в секундах счетчика
        self._datetime = datetime.datetime.now()
        self._indepetdent_time = self._time_counter.get_time_value()
        self._id = None

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    def set_registrator_info(self, registrator_info: ReceiptRegistratorData):
        self._registrator_info = registrator_info

    def open_shift(self):
        sleep(0.1)
        self._shift_opened()

    def _shift_opened(self):
        if not self._shift_is_open:
            self._shift_number += 1
            self._shift_is_open = True
            self._shift_datetime_open = datetime.datetime.now()

    def close_shift(self):
        sleep(0.1)
        if self._shift_is_open:
            self._shift_is_open = False
            self._shift_datetime_open = None
            self._shift_documents_count = 0

    def get_shift_info(self) -> ShiftInformation:
        shift_number = self._shift_number if self._shift_datetime_open else None
        return ShiftInformation(self._shift_is_open, datetime.datetime.now(), self._time_counter,
                                self._time_counter.get_time_value(), number=shift_number,
                                datetime_open=self._shift_datetime_open, datetime_closed=None)

    def register_receipt(self, receipt):
        logger.debug('Receipt %d registration on %s', receipt.id, str(self))
        self._shift_opened()
        values = [str(i) for i in range(10)]
        fiscal_sign = ''.join(random.choices(values, k=8))
        self._shift_documents_count += 1
        self._receipt_num += 1
        receipt.set_fiscal_data(fiscal_sign, datetime.datetime.now(), self.id, self._shift_number,
                                self._shift_documents_count,  self._receipt_num)

    def get_registrator_info(self):
        return self._registrator_info

    def set_date_time(self, date_time: datetime.datetime):
        self._datetime = datetime.datetime.now()
        self._indepetdent_time = self._time_counter.get_time_value()

    def get_date_time(self):
        return self._datetime + datetime.timedelta(seconds=self._time_counter.get_time_value() - self._indepetdent_time)

    def reboot(self):
        pass

    def close(self):
        pass