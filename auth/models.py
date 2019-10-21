from db import model
import asyncio

users_dict = {'vhshop': {'id': 1, 'group_id': 1, 'passwd': 'jQuery770771@', 'notifier': {
    'name': 'Http_json_notifier', 'config': {'url': 'http://127.0.0.1', 'port': '2477',
                                             'user': 'bbb', 'passw': 'aaa'}
}
                         }}


class User(model.Model):

    async def get_user(self, login, passwd):
        await asyncio.sleep(0)
        try:
            user_data = users_dict[login].copy()
            if user_data['passwd'] != passwd:
                self._authentication_fail()
                return False
            else:
                user_data.pop('passwd')
                self.id = user_data['id']
                self.login = login
                self.is_authenticated = True
                self.notifier = user_data['notifier']

        except:
            self._authentication_fail()
            return False

    async def get_notifier(self):
        await asyncio.sleep(0)
        user_data = users_dict.get(self.login)
        return user_data.get('notifier')

    def _authentication_fail(self):
        self.is_authenticated = False
        self.id = None
