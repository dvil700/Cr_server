from typing import Generator, Union
from access_control.abac.storages.base import AsyncStorage, PolicyDoesNotExist
from py_abac.storage.memory import MemoryStorage
from py_abac.policy import Policy


class InMemoryStorage(AsyncStorage):
    def __init__(self):
        self._storage = MemoryStorage()

    async def add(self, policy: Policy):
        self._storage.add(policy)

    async def get(self, uid: str) -> Union[Policy, None]:
        return self._storage.get(uid, None)

    async def get_all(self, limit: int, offset: int) -> Generator[Policy, None, None]:
        return self._storage.get_all(limit, offset)

    async def get_for_target(
            self,
            subject_id: str,
            resource_id: str,
            action_id: str
    ) -> Generator[Policy, None, None]:
        targets = {'subject_id':subject_id, 'resource_id':resource_id, 'action_id':action_id}
        for policy in self._storage.get_for_target(subject_id, resource_id, action_id):
            check = True
            for key, target in targets.items():
                if not target:
                    continue
                if target != getattr(policy.targets, key):
                    check = False
                    break
            if check:
                yield policy

    async def update(self, policy: Policy):
        self._storage.update(policy)

    async def delete(self, uid: str):
        try:
           self._storage.delete(uid)
        except ValueError as e:
            raise PolicyDoesNotExist(str(e))