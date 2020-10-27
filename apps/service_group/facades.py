from abc import ABC, abstractmethod
from typing import Iterable
from .storages.storages import AbstractServiceGroupStorage, ServiceGroupNotExists
from .service_group import ServiceGroup


class AbstractFiscalServiceGroupFacade(ABC):
    @abstractmethod
    async def register_new_service_group(self, name: str, is_enabled: bool, settings: dict) -> ServiceGroup:
        pass

    @abstractmethod
    async def update_service_group_information(self, group_id, name: str, is_enabled: bool, settings: dict):
        pass

    @abstractmethod
    async def get_service_group(self, service_group_id) -> ServiceGroup:
        pass

    @abstractmethod
    async def get_service_groups(self) -> Iterable:
        pass

    @abstractmethod
    async def delete_service_group(self, group_id):
        pass


class FiscalServiceGroupFacade(AbstractFiscalServiceGroupFacade):
    def __init__(self, storage: AbstractServiceGroupStorage):
        self._storage = storage

    def _create_service_group(self, name: str, is_enabled: bool, settings: dict) -> ServiceGroup:
        return ServiceGroup(None, name, is_enabled, settings)

    async def register_new_service_group(self, name: str, is_enabled: bool, settings: dict):
        service_group = self._create_service_group(name, is_enabled, settings)
        await self._storage.add(service_group)
        return service_group

    async def update_service_group_information(self, id, name: str, is_enabled: bool, settings: dict):
        service_group = await self.get_service_group(id)
        service_group.name = name
        service_group.is_enabled = is_enabled
        service_group.settings = settings
        await self._storage.update(service_group)

    async def get_service_group(self, service_group_id) -> ServiceGroup:
        try:
            service_group = await self._storage.get(service_group_id)
        except ServiceGroupNotExists as e:
            raise e
        return service_group

    async def get_service_groups(self):
        return await self._storage.get_service_groups()

    async def delete_service_group(self, group_id):
        await self._storage.delete(group_id)

