import pytest
from collections import namedtuple
from py_abac import Request, Policy
from access_control.abac.storages.in_memory.storages import InMemoryStorage
from access_control.abac import AsyncPDB
from access_control.services import AccessAdministrationService


pytestmark = pytest.mark.asyncio


class TestAbac:
    def get_json(self, user_id, resource_id, method):
        return {
            "subject": {
                "id": user_id,
                "attributes": {"user_id": user_id}
            },
            "resource": {
                "id": resource_id,
                "attributes": {"resource_id": resource_id}
            },
            "action": {
                "id": "",
                "attributes": {"method": method}
            }
        }

    async def test_service(self):
        storage = InMemoryStorage()
        service = AccessAdministrationService(storage)
        Access_item = namedtuple('Access_item', ['user_id', 'resource_id', 'get', 'post', 'delete'])
        access_data = (Access_item('1', 'admin', True, True, True),
                       Access_item('2', 'admin', True, True, True),
                       Access_item('3', 'res_14', True, True, True),
                       Access_item('4', 'res_14', True, True, False),
                       Access_item('5', 'res_15', True, True, False))

        for item in access_data:
            await service.set_access_policy(*item)


        admin_policies = [policy async for policy in service.get_resource_policies('admin')]
        assert len(admin_policies) == 2
        res_14_policies = [policy async for policy in service.get_resource_policies('res_14')]
        assert len(res_14_policies) == 2
        res_15_policies = [policy async for policy in service.get_resource_policies('res_15')]
        assert len(res_15_policies) == 1

        pdp = AsyncPDB(storage)

        wrong_user_id = '664353'
        wrong_resource_id = 'xxxxxxxx'

        for item in access_data:
            assert item.get == await pdp.is_allowed(Request.from_json(self.get_json(item.user_id, item.resource_id, 'get')))
            assert item.post == await pdp.is_allowed(Request.from_json(self.get_json(item.user_id, item.resource_id, 'post')))
            assert item.delete == await pdp.is_allowed(Request.from_json(self.get_json(item.user_id, item.resource_id, 'delete')))

            assert not await pdp.is_allowed(Request.from_json(self.get_json(wrong_user_id, item.resource_id, 'get')))
            assert not await pdp.is_allowed(Request.from_json(self.get_json(wrong_user_id, item.resource_id, 'post')))
            assert not await pdp.is_allowed(Request.from_json(self.get_json(wrong_user_id, item.resource_id, 'delete')))

            assert not await pdp.is_allowed(Request.from_json(self.get_json(item.user_id, wrong_resource_id, 'get')))
            assert not await pdp.is_allowed(Request.from_json(self.get_json(item.user_id, wrong_resource_id, 'post')))
            assert not await pdp.is_allowed(Request.from_json(self.get_json(item.user_id, wrong_resource_id, 'delete')))

        item = access_data[0]
        other = access_data[4]

        assert item.get != await pdp.is_allowed(Request.from_json(self.get_json(other.user_id, item.resource_id, 'get')))
        assert item.post != await pdp.is_allowed(Request.from_json(self.get_json(other.user_id, item.resource_id, 'post')))
        assert item.delete != await pdp.is_allowed(Request.from_json(self.get_json(other.user_id, item.resource_id, 'delete')))
