from aiohttp_security import AbstractAuthorizationPolicy
from auth.auth import authorized_id


class MainAuthorizationPolicy(AbstractAuthorizationPolicy):
    async def permits(self, identity, concrete_permission, context=None):
        raise Exception(text="Method 'permits' isn't supported ")

    async def authorized_userid(self, identity):
        user = await authorized_id(identity)
        return user

