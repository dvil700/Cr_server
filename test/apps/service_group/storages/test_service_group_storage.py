import pytest
from apps.service_group import ServiceGroup
from apps.service_group.storages import ServiceGroupSQLStorage, AbstractServiceGroupStorage, ServiceGroupNotExists

from core.db.engines.aiopg import AutocommitConnManager
from aiopg.sa import create_engine

pytestmark = pytest.mark.asyncio


@pytest.yield_fixture
async def storage():
    async with create_engine(user='test_user',
                             database='test_db',
                             host='127.0.0.1',
                             password='test') as engine:
        manager = AutocommitConnManager(engine)
        yield ServiceGroupSQLStorage(manager)
        #yield ServiceGroupInMemoryStorage()


class TestStorage:
    async def test_add(self, storage:  AbstractServiceGroupStorage):
        service_group = ServiceGroup(None, 'group1', True, {'default_setting':1})
        await storage.add(service_group)
        assert service_group.id > 0
        await storage.delete(service_group.id)

    async def test_get(self, storage:  AbstractServiceGroupStorage):
        service_group = ServiceGroup(None, 'group1', True, {'default_setting':1})
        await storage.add(service_group)
        gotten_service_group = await storage.get(service_group.id)
        assert gotten_service_group.id == service_group.id
        await storage.delete(service_group.id)
        try:
            await storage.get(service_group.id)
        except ServiceGroupNotExists:
            assert True
        else:
            assert False

    async def test_update(self, storage:  AbstractServiceGroupStorage):
        service_group = ServiceGroup(None, 'group1', True, {'default_setting':1})
        await storage.add(service_group)
        new_name = 'new_name'
        service_group.name = 'new_name'
        await storage.update(service_group)
        gotten_service_group = await storage.get(service_group.id)
        assert service_group.name == gotten_service_group.name
        await storage.delete(service_group.id)

    async def get_service_groups(self, storage:  AbstractServiceGroupStorage):
        data = [{'id': None, 'name': 'group1', 'is_enabled': True, 'settings': {'default_setting':1}},
                {'id': None, 'name': 'group2', 'is_enabled': False, 'settings': {'default_setting': 2}},
                {'id': None, 'name': 'group3', 'is_enabled': True, 'settings': {'default_setting': 3}}]

        for item in data:
            await storage.add(ServiceGroup(**item))

        service_groups = await storage.get_service_groups()
        for i, service_group in enumerate(service_groups):
            for key, item in data[i].items():
                assert item == getattr(service_group, key)
            await storage.delete(service_group.id)

