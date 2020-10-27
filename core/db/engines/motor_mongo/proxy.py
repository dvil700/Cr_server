from ... import DBManagerAbstract
from motor.motor_asyncio import AsyncIOMotorDatabase


class DBProxy(DBManagerAbstract, AsyncIOMotorDatabase):
    def __init__(self, motor_mongo_database: AsyncIOMotorDatabase):
        self._database = motor_mongo_database

    def __getattr__(self, item):
        return getattr(self._database)

    async def close(self):
        await self._database.client.close()