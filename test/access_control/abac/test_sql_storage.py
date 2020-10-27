import pytest
from py_abac import Request, Policy
from aiopg.sa import create_engine
from access_control.abac.storages.sql import AsyncSQLStorage
from access_control.abac import AsyncPDB
from core.db.engines.aiopg import AutocommitConnManager

pytestmark = pytest.mark.asyncio


@pytest.yield_fixture
async def db_manager():
    try:
        async with create_engine(user='test_user',
                             database='test_db',
                             host='127.0.0.1',
                             password='test') as engine:
            manager = AutocommitConnManager(engine)
            yield manager
    except:
        pass


class TestAbac:
    async def test_abac(self, db_manager):
        policy_json = {
            "uid": "1",
            "description": "Max and Nina are allowed to create, delete, get any "
                           "resources only if the client IP matches.",
            "effect": "allow",
            "rules": {
                "subject": [{"$.name": {"condition": "Equals", "value": "Max"}},
                            {"$.name": {"condition": "Equals", "value": "Nina"}}],
                "resource": {"$.name": {"condition": "RegexMatch", "value": ".*"}},
                "action": [{"$.method": {"condition": "Equals", "value": "create"}},
                           {"$.method": {"condition": "Equals", "value": "delete"}},
                           {"$.method": {"condition": "Equals", "value": "get"}}],
                "context": {"$.ip": {"condition": "CIDR", "value": "127.0.0.1/32"}}
            },
            "targets": {},
            "priority": 0
        }

        # Parse JSON and create policy object
        policy = Policy.from_json(policy_json)

        # Setup policy storage
        storage = AsyncSQLStorage(db_manager)
        # Add policy to storage
        await storage.add(policy)

        # Create policy decision point
        pdp = AsyncPDB(storage)

        # A sample access request JSON+
        request_json = {
            "subject": {
                "id": "",
                "attributes": {"name": "Max"}
            },
            "resource": {
                "id": "",
                "attributes": {"name": "myrn:example.com:resource:123"}
            },
            "action": {
                "id": "",
                "attributes": {"method": "get"}
            },
            "context": {
                "ip": "127.0.0.1"
            }
        }
        # Parse JSON and create access request object
        request = Request.from_json(request_json)

        # Check if access request is allowed. Evaluates to True since
        # Max is allowed to get any resource when client IP matches.
        assert (await pdp.is_allowed(request))