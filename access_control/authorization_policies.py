from aiohttp_security import AbstractAuthorizationPolicy
from .abac.pbp import AbstractAsyncPDP, AccessRequest
from .auth.services import AbstractAuthenticationService, UserDoesNotExist


class AbacAuthorizationPolicy(AbstractAuthorizationPolicy):
    def __init__(self, pdp: AbstractAsyncPDP, authentication_service: AbstractAuthenticationService):
        self._pdp = pdp
        self._authentication_service = authentication_service

    async def permits(self, identity, resource, context=None):
        if not context:
            return False
        identity = str(identity)
        request_json = {
            "subject": {
                "id": identity,
                "attributes": {"user_id": identity}
            },
            "resource": {
                "id": resource,
                "attributes": {"resource_id": resource}
            },
            "action": {
                "id": "",
                "attributes": {"method": str(context['method']).lower()}
            }
        }
        # Parse JSON and create access request object
        request = AccessRequest.from_json(request_json)
        return await self._pdp.is_allowed(request)

    async def authorized_userid(self, identity):
        try:
            user = await self._authentication_service.get_user(int(identity))
        except UserDoesNotExist:
            return None
        else:
            return user
