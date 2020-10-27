from aiohttp import web, hdrs, BasicAuth
from aiohttp_security import AbstractAuthorizationPolicy
from .auth import AbstractAuthenticationService
from . import AbstractAttributesCalculation


@web.middleware
class BasicAuthMiddleware:
    @staticmethod
    def _get_app_auth_service(request) -> AbstractAuthenticationService:
        try:
            authentication_service = request.app['authentication_service']
        except KeyError:
            raise web.HTTPInternalServerError(text='The app authentication_service is not initialized')
        return authentication_service

    @staticmethod
    def _get_app_authorization_policy(request) -> AbstractAuthorizationPolicy:
        try:
            authorization_policy = request.app['authorization_policy']
        except KeyError:
            raise web.HTTPInternalServerError(text='The app authorization policy is not initialized')
        return authorization_policy

    @staticmethod
    def _get_access_attr_calc_strategy(request) -> AbstractAttributesCalculation:
        try:
            calc_strategy = request.app['access_attr_calc_strategy']
        except KeyError:
            raise web.HTTPInternalServerError(text='The app permission calculation strategy is not set')
        return calc_strategy

    def _get_resource_id(self, request):
        strategy = self._get_access_attr_calc_strategy(request)
        return strategy.get_resource_id(request)

    def _get_context(self, request):
        strategy = self._get_access_attr_calc_strategy(request)
        return strategy.get_context(request)

    async def __call__(self, request, handler):

        auth_header = request.headers.get(hdrs.AUTHORIZATION)
        if not auth_header:
            raise web.HTTPUnauthorized
        try:
            credentials = BasicAuth.decode(auth_header=auth_header)
        except ValueError as e:
            raise web.HTTPUnauthorized(text=str(e))

        auth_service = self._get_app_auth_service(request)
        user = await auth_service.authenticate(login=credentials.login, passwd=credentials.password)
        if not user:
            raise web.HTTPUnauthorized
        access = await self._get_app_authorization_policy(request).permits(user.id, self._get_resource_id(request),
                                                                           self._get_context(request))
        if not access:
            raise web.HTTPForbidden
        request['user'] = user
        return await handler(request)

