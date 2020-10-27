from abc import ABC, abstractmethod
from datetime import datetime
from logging import getLogger


logger = getLogger(__name__)


class ReceiptNotExists(Exception):
    pass


class AbstractReceiptRepository(ABC):
    @abstractmethod
    def save(self, data: dict):
        pass

    @abstractmethod
    def update(self, data: dict):
        pass

    @abstractmethod
    def get(self, receipt_id, company_id) -> dict:
        pass

    @abstractmethod
    def get_receipt_list(self, company_id, date_start, date_end, order_id, asc=True) -> list:
        pass

    @abstractmethod
    def get_last_id(self):
        pass


class MongoMotorReceiptRepository(AbstractReceiptRepository):
    def __init__(self, database):
        self._collection = database.receipt

    async def save(self, data: dict):
        data = data.copy()
        receipt_id = data.pop('id')
        await self._collection.replace_one({'_id': receipt_id}, data, True)

    async def update(self, data: dict):
        data = data.copy()
        receipt_id = data.pop('id')
        await self._collection.update_one({'_id': receipt_id}, {'$set': data})

    async def get(self, receipt_id, company_id) -> dict:
        return await self._collection.find_one({'_id': receipt_id, 'company_id': company_id})

    async def get_receipt_list(self, company_id, date_start, date_end, order_id=None, asc=True) -> list:
        result = []
        sort_order = 1 if asc else -1
        conditions = {'company_id': company_id, 'registration_datetime': {'$gte': date_start, '$lt': date_end}}
        if order_id:
            conditions['order_id'] = order_id
        async for document in await self._collection.find(conditions).sort('_id', sort_order):
            result.append(document)
        return result

    async def get_last_id(self):
        async for document in self._collection.find().sort('_id', -1).limit(1):
            return document['_id'] + 1
        return 1


class InMemoryReceiptRepository(AbstractReceiptRepository):
    def __init__(self):
        self._collection = {}
        self._max_id = 0

    async def save(self, data: dict):
        self._collection[data['id']] = data
        self._max_id = data['id'] if data['id'] > self._max_id else self._max_id

    async def update(self, data: dict):
        try:
            self._collection[data['id']].update(data)
        except KeyError:
            logger.error('Unable to update receipt data, the record with id %d  does not exist', data['id'])
            raise ReceiptNotExists

    async def get(self, receipt_id, company_id):
        try:
            receipt = self._collection[receipt_id]
        except KeyError:
            raise ReceiptNotExists
        if receipt['service_id']:
            return receipt.copy()
        raise ReceiptNotExists

    async def get_receipt_list(self, company_id, date_start, date_end, order_id=None, asc=True):
        datetime_modify = lambda item: item if item.get('registration_datetime', None) else datetime.now()
        filt_fun = lambda x: x['company_id'] == company_id and date_start <= datetime_modify(x) <= date_end and \
                             x['order_id'] == order_id
        return [item.copy() for item in self._collection.values() if filt_fun(item)]

    async def get_last_id(self):
        return self._max_id
