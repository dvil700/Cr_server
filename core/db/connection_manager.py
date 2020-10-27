from abc import ABC, abstractmethod
from typing import ContextManager


class AbstractConnectionManager(ABC):
    @abstractmethod
    async def connection(self) -> ContextManager:
        pass
