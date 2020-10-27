from aiopg.sa import create_engine
import pytest
from access_control.auth import UserSQLRepository
from core.db.engines.aiopg import AutocommitConnManager
from access_control.auth import UserFactory

pytestmark = pytest.mark.asyncio


@pytest.yield_fixture
async def repository():
    async with create_engine(user='test_user',
                             database='test_db',
                             host='127.0.0.1',
                             password='test') as engine:
        manager = AutocommitConnManager(engine)
        yield UserSQLRepository(manager)



class TestRep:
    async def test_add(self, repository):
        user = UserFactory().create_user(None, 'user1', 'dv@mm.ru', 'ddd323432','', True )
        await repository.add(user)
        user_get = await repository.get(user.id)
        assert user == user_get

    async def test_update(self, repository):
        user = UserFactory().create_user(None, 'user1', 'dv@mm.ru', 'ddd323432','', True )
        await repository.add(user)
        user.info = 'Changed info'
        await repository.update(user)
        user_get = await repository.get(user.id)
        assert user == user_get


    async def test_user_list_request(self, repository):
        users = []
        users.append(UserFactory().create_user(None, 'userOne', 'ddd@b.ru', 'info1', '', True))
        users.append(UserFactory().create_user(None, 'userTwo', 'dv@mm.ru', 'info2', '', True))
        users.append(UserFactory().create_user(None, 'userThree', 'dv33@moo.ru', 'info3', '', True))
        for user in users:
            await repository.add(user)
        users_list = await repository.get_users_list('id', 1, 200)