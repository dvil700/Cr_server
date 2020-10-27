from .domain import Receipt
from core.events.events import Event
import datetime


class ReceiptCreated(Event):
    def __init__(self, receipt):
        self._entity ='receipt'
        self._entity_id = receipt.id
        self._date_time = datetime.datetime.utcnow()
        self._data = receipt.as_dict()
        self._data['state'] = 'created'
        self._user_id = receipt.user_id
        self._client_id = receipt.service_id


class ReceiptRegistered(Event):
    def __init__(self, receipt: Receipt):
        self._user_id = receipt.user_id
        self._client_id = receipt.service_id
        self._entity = 'receipt'
        self._entity_id = receipt.id
        self._data = {'registrator_id': receipt.registrator_id, 'fiscal_sign': receipt.fiscal_sign,
                      'registration_datetime': receipt.registration_datetime,
                      'self._cashier': receipt.cashier,'shift_num': receipt.shift_num,
                      'receipt_in_shift_num': receipt.receipt_in_shift_num, 'tax_system': receipt.tax_system,
                      'state': 'success'}
        self._date_time = datetime.datetime.now()


class ReceiptRegistationFailed(Event):
    def __init__(self, receipt: Receipt):
        self._user_id = receipt.user_id
        self._client_id = receipt.service_id
        self._entity = 'receipt'
        self._entity_id = receipt.id
        self._data = {'state': 'failed'}
        self._date_time = datetime.datetime.now()