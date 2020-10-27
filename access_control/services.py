from abc import ABC, abstractmethod
from typing import List
from collections import namedtuple
from py_abac import Policy
from .abac import PolicyExistsError, PolicyDoesNotExist
from .abac import AsyncStorage


UserAccessSettings = namedtuple('UserAccessSettings', ['user_id', 'resource', 'get', 'post', 'delete'])


class AbstractAccessAdministrationService(ABC):
    @abstractmethod
    async def set_access_policy(self, user_id, resource, get=False, post=False, delete=False):
        pass

    @abstractmethod
    async def unset_access_policy(self, user_id, resource):
        pass

    @abstractmethod
    async def delete_resource_access_data(self, resource):
        pass

    @abstractmethod
    async def get_resource_policies(self, resource_id, subject_id=''):
        pass

    @abstractmethod
    async def get_resource_access_settings(self, resource_id, subject_id='') -> List[UserAccessSettings,]:
        pass

    @abstractmethod
    async def delete_user_access_data(self, user_id: str):
        pass


class AccessAdministrationService(AbstractAccessAdministrationService):
    _methods = ('get', 'post', 'delete')

    def __init__(self, storage: AsyncStorage):
        self._storage = storage

    def _create_policy(self, user_id: str, resource_id: str, get=False, post=False, delete=False):
        actions_dict = {'get': get, 'post': post, 'delete': delete}
        policy_json = {
            "uid": '_'.join((user_id, resource_id,)),
            "description": "",
            "effect": "allow",
            "rules": {
                "subject": {"$.user_id": {"condition": "Equals", "value": user_id}},
                "resource": {"$.resource_id": {"condition": "RegexMatch", "value": resource_id}},
                "action": [{"$.method": {"condition": "Equals", "value": key}} for key, item in actions_dict.items() if
                           item],
                "context": {}
            },
            "targets": {"subject_id": user_id, "resource_id": resource_id},
            "priority": 0
        }
        return Policy.from_json(policy_json)

    async def set_access_policy(self, user_id: str, resource_id: str, get=False, post=False, delete=False):
        policy = self._create_policy(user_id, resource_id, get, post, delete)
        await self._storage.add(policy)

    async def update_access_policy(self, user_id: str, resource_id: str, get=False, post=False, delete=False):
        policy = self._create_policy(user_id, resource_id, get, post, delete)
        await self._storage.update(policy)

    async def unset_access_policy(self, user_id, resource_id):
        try:
            await self._storage.delete('_'.join((user_id, resource_id,)))
        except PolicyDoesNotExist as e:
            raise e

    async def delete_resource_access_data(self, resource_id):
        async for policy in self.get_resource_policies(resource_id):
            await self._storage.delete(policy.uid)

    async def delete_user_access_data(self, user_id):
        async for policy in self._storage.get_for_target(user_id, '', ''):
            await self._storage.delete(policy.id)

    async def get_resource_policies(self, resource_id, subject_id=''):
        async for item in self._storage.get_for_target(subject_id, resource_id, ''):
            yield item

    async def get_resource_access_settings(self, resource_id, subject_id='') -> List[UserAccessSettings,]:
        users_access_settings = []
        async for policy in self.get_resource_policies(resource_id, subject_id):
            user_id = policy.rules.subject['$.user_id'].value
            methods = [item['$.method'].value for item in policy.rules.action]
            users_access_settings.append(UserAccessSettings(user_id, resource_id, *[m in methods for m in self._methods]))
        return users_access_settings


