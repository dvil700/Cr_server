from abc import ABC, abstractmethod
from aiohttp.web import BaseRequest


class AbstractAttributesCalculation(ABC):
    @abstractmethod
    def get_resource_id(self, request: BaseRequest) -> str:
        pass

    @abstractmethod
    def get_context(self, request: BaseRequest) -> dict:
        pass
