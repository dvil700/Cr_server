from abc import ABC, abstractmethod
from ..domain import ReceiptRegistratorData
from hashlib import sha1


class RegistratorDataNotExists(Exception):
    pass


class RegistratorDataExists(Exception):
    pass


class AbstractRegistratorDataStorage(ABC):
    @abstractmethod
    async def get(self, registrator_id) -> ReceiptRegistratorData:
        pass

    @abstractmethod
    async def get_id(self, registrator_data) -> int:
        pass

    @abstractmethod
    async def add(self, data: ReceiptRegistratorData) -> int:
        pass

    @abstractmethod
    async def get_registrators_by_sn(self, serial_number: str) -> list:
        pass

    @abstractmethod
    async def get_registrators_by_company_inn(self, inn: str) -> list:
        pass

    @abstractmethod
    async def get_last_id(self) -> int:
        pass


class MotorMongoRegistratorInfoStorage(AbstractRegistratorDataStorage):
    def __init__(self, db):
        self._collection = db.registrator_info
        self._current_id = 0

    @staticmethod
    def _hash(registrator_data):
        return sha1(';'.join(registrator_data).encode()).hexdigest()

    async def add(self, registrator_data: ReceiptRegistratorData):
        self._current_id = (await self.get_last_id()) + 1
        data = registrator_data.as_dict()
        data['hash'] = self._hash(registrator_data)
        data['_id'] = self._current_id
        await self._collection.insert(data)
        return data['_id']

    async def get(self, registrator_id):
        data = await self._collection.find_one({'_id': registrator_id})
        data['id'] = data.pop('_id')
        data.pop('hash')
        if not data:
            raise RegistratorDataNotExists
        return data

    async def get_id(self, registrator_data):
        async for data in await self._collection.find({'hash': self._hash(registrator_data)}):
            data.pop('hash')
            registrator_id = data.pop('_id')
            if data == registrator_data.as_dict():
                return registrator_id
        raise RegistratorDataNotExists

    async def get_last_id(self):
        if self._current_id:
            return self._current_id
        async for document in await self._collection.find().sort('_id', -1).limit(1):
            return document['_id']

    async def get_registrators_by_sn(self, serial_number: str) -> list:
        pass

    async def get_registrators_by_company_inn(self, inn: str) -> list:
        pass


class InMemoryRegistratorInfoStorage(AbstractRegistratorDataStorage):
    def __init__(self):
        self._collection = {}
        self._hash_index = {}
        self._current_id = 0

    def _hash(self, registrator_data):
        return sha1(';'.join(registrator_data).encode()).hexdigest()

    async def add(self, registrator_data):
        data_hash = self._hash(registrator_data)
        for item in self._collection.values():
            if item['hash'] == data_hash:
                raise RegistratorDataExists
        data = {'data': registrator_data, 'hash': data_hash, 'id': (await self.get_last_id()) + 1}
        self._collection[data['id']] = data
        return data['id']

    async def get(self, registrator_id):
        try:
            data = self._collection[registrator_id]
        except KeyError:
            raise RegistratorDataNotExists
        return ReceiptRegistratorData(data['registration_number'], data['registrator_serial'], data['fn_serial'],
                                      data['ffd_version'], data['ofd_name'], data['ffd_inn'], data['company_name'],
                                      data['company_inn'], data['operations_address'], data['operations_place'])

    async def get_id(self, registrator_data):
        result = list(filter(lambda x: x['data'] == registrator_data, self._collection.values()))
        assert len(result) < 2, 'There must not be more than one item in the result'
        if len(result) == 1:
            return result[0]
        raise RegistratorDataNotExists

    async def get_last_id(self):
        return self._current_id

    async def get_registrators_by_sn(self, serial_number: str) -> list:
        pass

    async def get_registrators_by_company_inn(self, inn: str) -> list:
        pass