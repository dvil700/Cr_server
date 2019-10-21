import asyncio


class Invoker():  # реализует очередь с приоритетами для команд и их последовательное исполнение
    def __init__(self, cr_adapter, loop):
        self.storage = asyncio.PriorityQueue()  # хранилище команд на исполнение, очередь с приоритетами
        self.lock = asyncio.Lock()
        self.loop = loop
        self.cr_adapter = cr_adapter
        self.current_task = None

    async def _execute(self):
        async with self.lock:
            command = self.storage.get_nowait()
            result = await command.execute(self.cr_adapter)
        if self.storage.qsize() > 0:
            self.current_task = self.loop.create_task(self._execute())

    async def put(self, command):
        self.storage.put_nowait(command)
        if self.storage.qsize() == 1:
            await self._execute()
        else:
            await asyncio.sleep(0)

    def __str__(self):
        return self.storage.__str__()

    async def close(self):
        await self.storage.join()
