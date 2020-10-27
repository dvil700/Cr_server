from aiopg.sa import Engine
from ... import DBManagerAbstract


class EngineProxy(Engine, DBManagerAbstract):
    def __init__(self, engine_context_manager: Engine):
        self._engine_context_manager = engine_context_manager
        self._engine = None
        self._gen = self._get_gen()

    async def _get_gen(self):
        async with self._engine_context_manager as engine:
            yield engine

    @classmethod
    async def create(cls, engine_context_manager):
        instance = cls(engine_context_manager)
        await instance.init()
        return instance

    async def init(self):
        if not self._engine:
            self._engine = await self._gen.__anext__()

    @property
    def dialect(self):
        return self._engine._dialect

    @property
    def name(self):
        return self._engine._dialect.name

    @property
    def driver(self):
        return self._engine.driver

    @property
    def dsn(self):
        """DSN connection info"""
        return self._engine.dsn

    @property
    def timeout(self):
        return self._engine.timeout

    @property
    def minsize(self):
        return self._engine.minsize

    @property
    def maxsize(self):
        return self._engine.maxsize

    @property
    def size(self):
        return self._engine.size

    @property
    def freesize(self):
        return self._engine.freesize

    @property
    def closed(self):
        return self._engine.closed

    def terminate(self):
        self._engine.terminate()

    async def wait_closed(self):
        await self._engine.wait_closed()

    def acquire(self):
        return  self._engine.acquire()

    def release(self, conn):
        return self._engine.release(conn)

    def __enter__(self):
        return self._engine.__enter__()

    def __exit__(self, *args):
        pass

    def __await__(self):
        return self._engine.__await__()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return await self._engine.__aexit__()

    async def close(self):
        await self._gen.__anext__()