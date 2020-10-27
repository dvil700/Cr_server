import re
from collections import namedtuple


class Email:
    __slots__ = ('_value', )

    def __init__(self, email: str):
        if len(email) > 256:
            raise ValueError('The length of email must be less then 256 characters')

        if not re.match(r'^([\w_\.+]|-)+@.+\.([\w_\.+]|-)+$', email):
            raise ValueError('The email is incorrect')

        self._value = email.lower()

    def __str__(self):
        return self._value

    def __repr__(self):
        return self._value

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return str(self) == str(other)

    def set_new_value(self, value: str):
        return self.__class__(value)


class Login:
    __slots__ = ('_value', )

    def __init__(self, value):
        if len(value) > 16:
            raise ValueError('The length of login must be less then 16 characters')
        if not re.match(r'^\w+$', value):
            raise ValueError('The login is incorrect')
        self._value = value.lower()

    def __str__(self):
        return self._value

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return str(self) == str(other)

    def set_new_value(self, value: str):
        return self.__class__(value)


UserDescriptor = namedtuple('UserDescriptor', ['id', 'login', 'email', 'info', 'is_active'])


class User:
    __slots__ = '_user_id', '_login', '_email', '_password', '_info', '_is_active'

    def __init__(self, user_id, login: Login, email: Email, password: str, info: str, is_active: bool):
        self._user_id = user_id
        self._login = login
        self._password = password
        self._info = info
        self._is_active = is_active
        self._email = email

    @property
    def is_active(self):
        return self._is_active

    @is_active.setter
    def is_active(self, value):
        self._is_active = value

    @property
    def id(self):
        return self._user_id

    @id.setter
    def id(self, value):
        self._user_id = value

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, value: str):
        self._email = self._email.set_new_value(value)

    @property
    def login(self):
        return self._login

    @login.setter
    def login(self, value: str):
        self._login = self._login.set_new_value(value)

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, password: str):
        if self._password == password:
            raise ValueError('The password must be different then the current password')
        self._password = password

    @property
    def info(self):
        return self._info

    @info.setter
    def info(self, value: str):
        self._info = value

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        for key in self.__slots__:
            if getattr(self, key) != getattr(other, key):
                return False
        return True

    def get_descriptor(self):
        return UserDescriptor(self.id, str(self._login), str(self.email), str(self.info), self.is_active)


class UserFactory:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def create_user(self, id, login: str, email: str, password: str, info: str, is_active: bool):
        return User(id, Login(login), Email(email), password, info, is_active)