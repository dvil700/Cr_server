from abc import ABC, abstractmethod
from apps.service_group.service_group import ServiceGroup


class ServiceGroupNotExists(Exception):
    pass


class AbstractServiceGroupStorage(ABC):
    @abstractmethod
    async def add(self, service_group: ServiceGroup):
        pass

    @abstractmethod
    async def get(self, service_group_id) -> ServiceGroup:
        pass

    @abstractmethod
    async def update(self, service_group_info: ServiceGroup):
        pass

    @abstractmethod
    async def get_service_groups(self) -> list:
        pass

    @abstractmethod
    async def delete(self, service_group_id):
        pass
