from contextlib import asynccontextmanager
from ...connection_manager import AbstractConnectionManager


class AutocommitConnManager(AbstractConnectionManager):
    def __init__(self, engine):
        self._engine = engine

    @asynccontextmanager
    async def connection(self):
        async with self._engine.acquire() as conn:
            transaction = await conn.begin()
            try:
                yield conn
            except Exception as e:
                await transaction.rollback()
                raise e
            else:
                await transaction.commit()