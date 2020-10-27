from abc import ABC, abstractmethod
from typing import Iterable
from .user import UserDescriptor, User


class AbstractAuthenticationService(ABC):
    @abstractmethod
    async def authenticate(self, login, passwd) -> UserDescriptor:
        pass

    @abstractmethod
    async def get_user(self, user_id):
        pass


class AbstractUserManagmentService:
    @abstractmethod
    async def create_new_user(self, login: str, email: str, password: str, info: str, is_active: bool) -> User:
        pass

    @abstractmethod
    async def update_user(self, user_id, login=None, email=None, password=None, info=None, is_active=None):
        pass

    @abstractmethod
    async def get_users(self, order_by: str, offset: int, limit: int) -> Iterable:
        pass

    @abstractmethod
    async def get_user(self, user_id) -> UserDescriptor:
        pass

    @abstractmethod
    async def delete_user(self, user_id):
        pass
