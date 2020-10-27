import pytest
from py_abac import Request, Policy
from access_control.abac.storages.in_memory.storages import InMemoryStorage
from access_control.abac import AsyncPDB


pytestmark = pytest.mark.asyncio


class TestAbac:
    async def test_abac(self):
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
            "targets": {'resource_id':'xxx'},
            "priority": 0
        }

        # Parse JSON and create policy object
        policy = Policy.from_json(policy_json)

        # Setup policy storage
        storage = InMemoryStorage()
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
                "id": "xxx",
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
