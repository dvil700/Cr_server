from ...domain import AbstractUserRepository, UserExists, UserDoesNotExist


class UserInMemoryRepository(AbstractUserRepository):
    def __init__(self):
        self._users = {}
        self._counter = 1

    async def add(self, user):
        for us in self._users.values():
            if us.login == user.login:
                raise UserExists('The user with login {} already exists'.format(user.login))
        self._users[self._counter] = user
        user.id = self._counter
        self._counter += 1

    async def delete(self, user_id):
        try:
            del self._users[user_id]
        except KeyError:
            raise UserDoesNotExist('The user with id {} does not exist'.format(user_id))

    async def get(self, user_id):
        try:
            return self._users[user_id]
        except KeyError:
            raise UserDoesNotExist('The user with id {} does not exist'.format(user_id))

    async def get_by_login(self, login):
        for user in self._users.values():
            if str(user.login) == login.lower():
                return user
        raise UserDoesNotExist('The user with login {} does not exist'.format(login))

    async def update(self, user):
        if not self._users.get(user.id, None):
            raise UserDoesNotExist('The user with id {} does not exist'.format(user.id))
        self._users[user.id] = user

    async def get_users_list(self, order_by, offset, limit):
        sort_order = lambda x: getattr(x, order_by)
        return list(sorted(self._users.values(), key=sort_order))[offset: limit]
