import aiomysql
from aiomysql.sa import create_engine
import re


class DBaseMeta(type):
    def __call__(cls, *a, **k):
        if not getattr(cls, '_instance', None):
            cls._instance = super().__call__(*a, **k)
        return cls._instance


class SADataBase(metaclass=DBaseMeta):
    @classmethod
    async def connect(cls, config, charset, loop):
        pool = await create_engine(**config, charset=charset, loop=loop, autocommit=True)
        return cls(pool)

    def __init__(self, pool=None):
        if pool:
            self._pool = pool

    @property
    def dialect(self):
        return self._pool.dialect

    @property
    def pool(self):
        return self._pool

    @property
    def conn(self):
        return self._pool.acquire()

    async def query(self, request, params=None, rows=False):
        result = False
        async with self.conn as conn:
            if params is None:
                cur = await conn.execute(request)
            else:
                cur = await conn.execute(request, params)
            if re.match(r'^\s*insert', str(request), flags=re.IGNORECASE) is not None:
                result = cur.lastrowid
            elif re.match(r'^\s*select', str(request), flags=re.IGNORECASE):
                if rows:
                    result = await cur.fetchall()
                else:
                    result = await cur.fetchone()
            else:
                result = None
        return result

    async def close(self):
        self.pool.close()
        await self.pool.wait_closed()
        self.__class__._instance = None
