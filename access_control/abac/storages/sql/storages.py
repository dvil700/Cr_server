from typing import Union, Generator
import logging
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import FlushError
from sqlalchemy.orm import Query
from sqlalchemy import insert, update, delete
from py_abac.storage.sql.model import PolicyModel, ResourceTargetModel, SubjectTargetModel, ActionTargetModel
from core.db.connection_manager import AbstractConnectionManager
from access_control.abac.storages.base import AsyncStorage, Policy, PolicyDoesNotExist, PolicyExistsError


LOG = logging.getLogger(__name__)


class AsyncSQLStorage(AsyncStorage):
    _target_models = {'resources': ResourceTargetModel, 'subjects': SubjectTargetModel,
                          'actions': ActionTargetModel}

    def __init__(self, db_manager: AbstractConnectionManager):
        self.db_manager = db_manager

    async def add(self, policy: Policy):
        try:
            async with self.db_manager.connection() as conn:
                policy_model = PolicyModel.from_policy(policy)
                await conn.execute(insert(PolicyModel).values(uid=policy.uid, json=policy_model.json))
                subject_values = [{'target_id': sub.target_id, 'uid':policy.uid} for sub in policy_model.subjects]
                resource_values = [{'target_id': sub.target_id, 'uid': policy.uid} for sub in policy_model.resources]
                action_values = [{'target_id': sub.target_id, 'uid': policy.uid} for sub in policy_model.actions]
                await conn.execute(insert(SubjectTargetModel).values(subject_values))
                await conn.execute(insert(ResourceTargetModel).values(resource_values))
                await conn.execute(insert(ActionTargetModel).values(action_values))
            LOG.info("Added Policy: %s", policy)
        except (IntegrityError, FlushError):
            LOG.error("Error trying to create already existing policy with UID=%s.", policy.uid)
            raise PolicyExistsError(policy.uid)

    @staticmethod
    async def _get_one_policy_model_by_id(uid, db_connection):
        cur = await db_connection.execute(Query(PolicyModel).filter_by(uid=uid).statement)
        policy_data = await cur.fetchone()
        if not policy_data:
            raise PolicyDoesNotExist
        return PolicyModel(**policy_data)

    async def _set_targets_to_policy_model(self, policy_model, db_connection):
        for key, model in self._target_models.items():
            cursor = await db_connection.execute(Query(model).filter_by(uid=policy_model.uid).statement)
            for target in await cursor.fetchall():
                getattr(policy_model, key).append(model(**dict(target)))

    async def get(self, uid: str) -> Union[Policy, None]:
        async with self.db_manager.connection() as conn:
            policy_model = await self._get_one_policy_model_by_id(uid, conn)
            await self._set_targets_to_policy_model(policy_model, conn)
        return policy_model.to_policy()

    async def get_all(self, limit: int, offset: int) -> Generator[Policy, None, None]:
        async with self.db_manager.connection() as conn:
            cur = await conn.execute(Query(PolicyModel).filter().order_by(PolicyModel.uid.asc())\
                                     .slice(offset, offset + limit).statement)
            policy_data_list = await cur.fetchall()
            for policy_data in policy_data_list:
                policy_model = PolicyModel(**policy_data)
                await self._set_targets_to_policy_model(policy_model, conn)
                yield policy_model.to_policy()

    async def get_for_target(self, subject_id: str, resource_id: str, action_id: str):
        policy_filter = PolicyModel.get_filter(subject_id, resource_id, action_id)
        async with self.db_manager.connection() as conn:
            cur = await conn.execute(Query(PolicyModel).filter(*policy_filter).with_entities(PolicyModel.uid, PolicyModel.json).statement)
            results = await cur.fetchall()
            for res in results:
                policy_model = PolicyModel(**res)
                await self._set_targets_to_policy_model(policy_model, conn)
                yield policy_model.to_policy()

    async def update(self, policy: Policy):
        try:
            async with self.db_manager.connection() as conn:
                new_policy = PolicyModel.from_policy(policy)
                policy_model = await self._get_one_policy_model_by_id(policy.uid, conn)
                if policy_model.json!= new_policy.json:
                    statement = update(PolicyModel).values(json=new_policy.json).\
                                where(PolicyModel.uid == new_policy.uid).statement
                    await conn.execute(statement)

                if not policy_model:
                    return

                new_targets = {}

                for key, model in self._target_models.items():
                    new_targets[key] = {item['target_id'] for item in getattr(new_policy, key) if item.id}
                    cursor = await conn.execute(Query(model).filter_by(uid=policy.uid).statement)
                    targets_to_delete = []
                    for item in (await cursor.fetchall()):
                        if item['target_id'] in new_targets[key]:
                            new_targets[key].pop(item['target_id'])
                            continue
                        targets_to_delete.append(item['id'])
                    del_statement = Query(model).filter(getattr(model, key).id.in_(targets_to_delete)).delete().statement

                    await conn.execute(del_statement)

                    await conn.execute(insert(model).values(new_targets[key]))

        except IntegrityError:  # pragma: no cover
            raise  # pragma: no cover
        LOG.info('Updated Policy with UID=%s. New value is: %s', policy.uid, policy)

    async def delete(self, uid: str):
        async with self.db_manager.connection() as conn:
            await conn.execute(delete(PolicyModel).where(PolicyModel.uid == uid))
        LOG.info("Deleted Policy with UID=%s.", uid)