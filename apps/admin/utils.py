from aiohttp.web import Request
from access_control import AbstractAttributesCalculation


class AccessAttributesCalculationStrategy(AbstractAttributesCalculation):
    def get_resource_id(self, request: Request) -> str:
        return request.app['id']

    def get_context(self, request: Request) -> dict:
        return {'method': request.method.lower()}


