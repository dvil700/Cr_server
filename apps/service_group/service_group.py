from abc import ABC, abstractmethod
from typing import Union


class ServiceGroup:
    __slots__ = '_id', '_name', '_is_enabled', '_settings'

    def __init__(self, service_group_id: Union[int, None], name: str, is_enabled: bool, settings: dict):
        self._id = service_group_id
        self._name = name
        self._is_enabled = is_enabled
        self._settings = settings

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def is_enabled(self):
        return self._is_enabled

    @is_enabled.setter
    def is_enabled(self, value):
        _is_enabled = value

    @property
    def settings(self):
        return self._settings

    @settings.setter
    def settings(self, value):
        self._settings = value

    def as_dict(self):
        return {'id': self.id, 'name': self.name, 'is_enabled': self.is_enabled, 'settings': self.settings.copy()}


class AbstractServiceGroupFactory(ABC):
    @abstractmethod
    def create_service_group(self, service_group_id: Union[int, None], name: str, is_enabled: bool,
                             settings: dict) -> ServiceGroup:
        pass


class DefaultServiceGroupFactory(ABC):
    def create_service_group(self, service_group_id: Union[int, None], name: str, is_enabled: bool,
                             settings: dict) -> ServiceGroup:
        return ServiceGroup(service_group_id, name, is_enabled, settings)