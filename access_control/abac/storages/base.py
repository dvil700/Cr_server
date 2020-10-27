from typing import Generator, Union
from py_abac.storage.base import Storage
from py_abac.policy import Policy
from access_control.abac.exceptions import PolicyExistsError, PolicyDoesNotExist


class AsyncStorage(Storage):
    async def add(self, policy: Policy):
        pass

    async def get(self, uid: str) -> Union[Policy, None]:
        pass

    async def get_all(self, limit: int, offset: int) -> Generator[Policy, None, None]:
        pass

    async def get_for_target(
            self,
            subject_id: str,
            resource_id: str,
            action_id: str
    ) -> Generator[Policy, None, None]:
        pass

    async def update(self, policy: Policy):
        pass

    async def delete(self, uid: str):
        pass