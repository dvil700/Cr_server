from logging import getLogger
from sqlalchemy.orm import Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy import update, delete
from ...domain import AbstractUserRepository, UserExists, UserDoesNotExist
from ...domain.user import UserFactory
from ...domain.abstract_repositories import UsersProxy
from .models import User as UserModel

logger = getLogger(__name__)


class UserSQLRepository(AbstractUserRepository):
    def __init__(self, db_conn_manager):
        self._db_conn_manager = db_conn_manager

    async def add(self, user):
        statement = UserModel.__table__.insert().values(**self._get_dict_parameters(user))
        async with self._db_conn_manager.connection() as conn:
            try:
                cursor = await conn.execute(statement)
            except IntegrityError as e:
                logger.debug('Unable to add a user with login %s. IntegrityError occured %s', user.login, str(e))
                raise UserExists
            user.id = (await cursor.fetchone())[0]
            return user.id

    async def delete(self, user_id):
        statement = delete(UserModel).where(UserModel.id == user_id)
        async with self._db_conn_manager.connection() as conn:
            await conn.execute(statement)

    async def get(self, user_id):
        async with self._db_conn_manager.connection() as conn:
            cursor = await conn.execute(Query(UserModel).filter_by(id=user_id).statement)
            user_data = await cursor.fetchone()
        if not user_data:
            raise UserDoesNotExist('The user with id = %d does not exist', user_id)
        return UserFactory().create_user(**dict(user_data))

    async def get_by_login(self, login):
        async with self._db_conn_manager.connection() as conn:
            cursor = await conn.execute(Query(UserModel).filter_by(login=login).statement)
            user_data = await cursor.fetchone()
        if user_data:
            return UserFactory().create_user(**dict(user_data))

    async def update(self, user):
        params = self._get_dict_parameters(user)
        params.pop('id')
        statement = update(UserModel).values(params).where(UserModel.id == user.id)
        async with self._db_conn_manager.connection() as conn:
             await conn.execute(statement)

    async def get_users_list(self, order_by, offset, limit):
        statement = Query(UserModel).filter().with_entities(UserModel.id, UserModel.login, UserModel.info, UserModel.email).\
                    order_by(order_by).offset(offset).limit(limit).statement
        async with self._db_conn_manager.connection() as conn:
            cursor = await conn.execute(statement)
            result = await cursor.fetchall()
            return UsersProxy(result)

    def _get_dict_parameters(self, user):
        parameters = user.get_descriptor()._asdict()
        parameters['password'] = user.password
        if parameters['id'] is None:
            parameters.pop('id')
        return parameters