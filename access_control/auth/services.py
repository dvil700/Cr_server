from abc import ABC, abstractmethod
import hashlib
from .domain import AbstractUserRepository, UserDescriptor, UserDoesNotExist, UserExists
from . import AbstractUserManagmentService, AbstractAuthenticationService
from . import UserFactory


class AbstractEncryptionService(ABC):
    @abstractmethod
    def encrypt(self, value: str) -> str:
        pass


class EncryptionService(AbstractEncryptionService):
    def __init__(self, salt):
        self._salt = salt

    @property
    def salt(self):
        return self._salt

    def encrypt(self, value: str) -> str:
        return hashlib.sha256('%s%s'.format(self.salt, value).encode('utf-8')).hexdigest()


class UserManagementService(AbstractUserManagmentService):
    def __init__(self, user_repository: AbstractUserRepository, encryption_service: AbstractEncryptionService):
        self._repo = user_repository
        self._user_factory = UserFactory()
        self._encryption_service = encryption_service

    async def create_new_user(self, login: str, email: str, password: str, info: str, is_active: bool):
        password = self._encryption_service.encrypt(password)
        user = self._user_factory.create_user(None, login, email, password, info, is_active)
        try:
            await self._repo.add(user)
        except UserExists as e:
            raise e
        return user

    async def update_user(self, user_id, login=None, email=None, info=None, is_active=None, password=None):
        user = await self._repo.get(user_id)
        if login:
            user.login = login
        if email:
            user.email = email
        if info:
            user.info = info
        if is_active is not None:
            user.is_active = is_active
        if password:
            user.password = self._encryption_service.encrypt(password)
        await self._repo.update(user)

    async def delete_user(self, user_id):
        try:
            await self._repo.delete(user_id)
        except UserDoesNotExist as e:
            raise e

    async def get_user(self, user_id):
        return (await self._repo.get(user_id)).get_descriptor()

    async def get_users(self, order_by, offset, limit):
        return await self._repo.get_users_list(order_by, offset, limit)


class AuthService(AbstractAuthenticationService):
    def __init__(self, user_repository: AbstractUserRepository, encryption_service: AbstractEncryptionService):
        self._repo = user_repository
        self._encryption_service = encryption_service

    async def authenticate(self, login, passwd) -> UserDescriptor:
        try:
            user = await self._repo.get_by_login(login)
        except UserDoesNotExist as e:
            raise e

        if user.password == self._encryption_service.encrypt(passwd):
            return user.get_descriptor()
        raise 

    async def get_user(self, user_id):
        return await self._repo.get(user_id)