from aiohttp.web import Request
from access_control import AbstractAttributesCalculation


class AccessAttributesCalculation(AbstractAttributesCalculation):
    def get_resource_id(self, request: Request) -> str:
        return '_'.join(('service_group', request.match_info['service_group_id'],))

    def get_context(self, request: Request) -> dict:
        return {'method': request.method.lower()}


