from typing import Union
from sqlalchemy.orm import Query
from sqlalchemy import insert, update, delete
from ..storages import AbstractServiceGroupStorage, ServiceGroup, ServiceGroupNotExists
from .models import ServiceGroup as ServiceGroupModel
from core.db.connection_manager import AbstractConnectionManager


class ServiceGroupSQLStorage(AbstractServiceGroupStorage):
    def __init__(self, db_manager: AbstractConnectionManager):
        self.db_manager = db_manager

    def _create_service_group(self, id: Union[int, None], name: str, is_enabled: bool, settings: dict):
        return ServiceGroup(id, name, is_enabled, settings)

    async def add(self, service_group: ServiceGroup):
        statement = insert(ServiceGroupModel).values(name=service_group.name, is_enabled=service_group.is_enabled,
                                                     settings=service_group.settings)
        async with self.db_manager.connection() as conn:
            cursor = await conn.execute(statement)
            result = await cursor.fetchone()
        service_group.id = result['id']

    async def get(self, service_group_id) -> ServiceGroup:
        async with self.db_manager.connection() as conn:
            cursor = await conn.execute(Query(ServiceGroupModel).filter_by(id=service_group_id).statement)
            result = await cursor.fetchone()
        if not result:
            raise ServiceGroupNotExists('The service group with id {} does not  exist'.format(service_group_id))
        return self._create_service_group(**result)

    async def update(self, service_group: ServiceGroup):
        statement = update(ServiceGroupModel).\
            where(ServiceGroupModel.id == service_group.id).values(name=service_group.name,
                                                                   is_enabled=service_group.is_enabled,
                                                                   settings=service_group.settings)
        async with self.db_manager.connection() as conn:
            await conn.execute(statement)

    async def get_service_groups(self):
        async with self.db_manager.connection() as conn:
            cursor = await conn.execute(Query(ServiceGroupModel).filter().order_by('id').statement)
            result = await cursor.fetchall()
        service_groups = []
        for item in result:
            service_groups.append(self._create_service_group(**item))
        return service_groups

    async def delete(self, service_group_id):
        async with self.db_manager.connection() as conn:
            await conn.execute(delete(ServiceGroupModel).where(ServiceGroupModel.id == service_group_id))
