from auth.models import User, UserProxy, Guest
from abc import ABC, abstractmethod
import hashlib
import os


def auth_cache(func):
    _cache = {}

    def wrapper(*args, **kwargs):
        name = func.__name__
        if name not in _cache:
            _cache[name] = func(*args, **kwargs)
        return _cache[name]

    return wrapper


def get_standart_password_check_strategy():
    # соль достаем из переменной окружения
    salt = os.environ["PASS_SALT"]
    return PasswordCheck(salt)


@auth_cache
def _get_authentication_object():
    return BaseAuthentication(User, Guest, UserProxy, get_standart_password_check_strategy())


async def auth(login, passwd):
    auth_object = _get_authentication_object()
    return await auth_object.authenticate(login, passwd)


async def authorized_id(user_id):
    auth_object = _get_authentication_object()
    return await auth_object.get_user(user_id)


class AbstractAuthentication(ABC):
    @abstractmethod
    async def authenticate(self, login, passwd):
        pass

    @abstractmethod
    async def get_user(self, login):
        pass


class BaseAuthentication(AbstractAuthentication):
    def __init__(self, user_cls, guest_cls, user_proxy=None, pwd_checking_strategy=None):
        self.user_cls = user_cls
        self.guest_cls = guest_cls
        self.user_proxy = user_proxy
        self.pwd_checking_strategy = pwd_checking_strategy

    def _check_password(self, checking, original):
        return self.pwd_checking_strategy(checking, original)

    async def authenticate(self, login, passwd):
        user_cls = self.user_cls
        sql_request = user_cls.query.filter(user_cls.login == login, user_cls.enabled == True).statement
        result = await user_cls.conn.query(sql_request)
        if not result or not self._check_password(result['passwd'], passwd):
            return self.guest_cls()
        user_data = {key: result[key] for key in result.keys() if key != 'passwd'}
        return self._build_user_object(**user_data)

    async def get_user(self, user_id=None):
        if user_id is None:
            return self.guest_cls()
        user_cls = self.user_cls
        request = user_cls.query.filter(user_cls.id == user_id, user_cls.enabled == True). \
            with_entities(user_cls.id, user_cls.login, user_cls.enabled, user_cls.superuser).statement
        result = await user_cls.conn.query(request)
        if not result:
            return self.guest_cls()
        return self._build_user_object(**result)

    def _build_user_object(self, **kwargs):
        user = self.user_cls(**kwargs)
        if self.user_proxy:
            return (self.user_proxy(user))
        return self.user_cls(**kwargs)


class AbstractPasswordCheck(ABC):
    def __call__(self, checking, original):
        return self.check(checking, original)

    @abstractmethod
    def check(self, login, passwd):
        pass


class SimplePasswordCheck(AbstractPasswordCheck):

    def check(self, checking, original):
        return checking == original

    def password_encode(self, passwd):
        return passwd


class PasswordCheck(AbstractPasswordCheck):
    def __init__(self, salt):
        self._salt = salt

    @property
    def salt(self):
        return self._salt

    def check(self, checking, original):
        original = self.password_encode(checking)
        return checking == original

    def password_encode(self, passwd):
        return hashlib.sha256('%s%s'.format(self.salt, passwd).encode('utf-8')).hexdigest()
