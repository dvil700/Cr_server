from copy import deepcopy
from ..storages import AbstractServiceGroupStorage, ServiceGroup, ServiceGroupNotExists


class ServiceGroupInMemoryStorage(AbstractServiceGroupStorage):
    def __init__(self):
        self._data = {}
        self._id_counter = 0

    async def add(self, service_group: ServiceGroup):
        self._id_counter += 1
        self._data[self._id_counter] = service_group
        service_group.id = self._id_counter

    async def get(self, service_group_id) -> ServiceGroup:
        try:
            service_group = self._data[service_group_id]
        except KeyError:
            raise ServiceGroupNotExists('The service group with id {} does not  exist'.format(service_group_id))
        return deepcopy(service_group)

    async def update(self, service_group: ServiceGroup):
        self._data[service_group.id] = service_group

    async def get_service_groups(self):
        return [deepcopy(service_group) for service_group in self._data.values()]

    async def delete(self, service_group_id: int):
        try:
            del self._data[service_group_id]
        except KeyError:
            raise ServiceGroupNotExists('Service group with id {} does not exist'.format(service_group_id))