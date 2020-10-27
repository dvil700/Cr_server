from abc import ABC, abstractmethod
from typing import Iterable
from .user import UserFactory


class UserDoesNotExist(Exception):
    pass


class UserExists(Exception):
    pass


class UsersProxy:
    def __init__(self, users_data: list):
        self._users_data = users_data
        self._user_factory = UserFactory()

    def __iter__(self):
        for item in self._users_data:
            yield self._user_factory.create_user(**item)

    def __getitem__(self, item):
        return self._user_factory.create_user(self._users_data[item])


class AbstractUserRepository(ABC):
    @abstractmethod
    async def get(self, user_id):
        pass

    @abstractmethod
    async def get_by_login(self, login):
        pass

    @abstractmethod
    async def add(self, user):
        pass

    @abstractmethod
    async def delete(self, user_id):
        pass

    @abstractmethod
    async def update(self, user):
        pass

    @abstractmethod
    async def get_users_list(self, order_by, offset, limit) -> Iterable:
        pass


