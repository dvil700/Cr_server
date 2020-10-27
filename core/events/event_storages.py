from abc import ABC, abstractmethod
from core.events.events import Event


class AbstractEventStorage(ABC):
    @abstractmethod
    async def add(self, event: Event):
        pass

    @abstractmethod
    async def get_by_time(self, datetime_start, datetime_finish, event_types: list = None):
        pass

    @abstractmethod
    async def get_last_record(self):
        pass


class InMemoryEventStorage(AbstractEventStorage):
    def __init__(self):
        self._events = []

    async def add(self, event: Event):
        self._events.append(event)

    async def get_last_record(self):
        return self._events[-1]

    async def get_by_time(self, datetime_start, datetime_finish, event_types: list = None):
        type_compare = lambda event: type(event) in event_types if event_types else True
        date_compare = lambda event, start, finish: type_compare(event) if start<= event._datetime<=finish else False
        return list(filter(date_compare, self._events))