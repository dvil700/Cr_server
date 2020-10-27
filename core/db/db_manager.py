from abc import ABC, abstractmethod


class DBManagerAbstract:
    @abstractmethod
    async def close(self):
        pass
