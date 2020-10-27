from abc import ABC, abstractmethod
import datetime


class ExecutionFailedError(Exception):
    pass


class AbstractCommand(ABC):
    user_id: int
    _income_data_id: int
    datetime: datetime.datetime
    _priority: int

    @property
    def priority(self):
        return self._priority

    def __lt__(self, other):
        if not isinstance(other, AbstractCommand):
            raise TypeError
        if self.priority == other.priority:
            return self.datetime<other.datetime
        return self.priority < other.priority

    def __gt__(self, other):
        if not isinstance(other, AbstractCommand):
            raise TypeError
        if self.priority == other.priority:
            return self.datetime > other.datetime
        return self.priority > other.priority

    @property
    def income_data_id(self):
        return self._income_data_id

    @abstractmethod
    async def execute(self, executor):
        pass


class AbstractInvoker(ABC):
    @abstractmethod
    def put(self, command: AbstractCommand):
        pass