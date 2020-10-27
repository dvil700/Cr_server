from abc import ABC, abstractmethod
import datetime


class Event(ABC):
    _datetime: datetime.datetime
    _entity: str
    _data: dict
    _entity_id: int
    _user_id: int
    _client_id: int

    @property
    def data(self):
        return self._data

    @property
    def entity(self):
        return self._entity

    @property
    def entity_id(self):
        return self._entity_id

    @property
    def user_id(self):
        return self._user_id

    @property
    def date_time(self):
        return self._datetime


class AbstractEventHandler(ABC):
    @abstractmethod
    def handle(self, event):
        pass

    @abstractmethod
    def subscribe(self, event_dispatcher):
        pass






