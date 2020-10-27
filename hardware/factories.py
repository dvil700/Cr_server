from core.loaders import DefaultModuleLoader
from .adapters.base import AbstractRegistratorDriverAdapter, AsyncRegistrator, DefaultStateFactory, AsyncTreadPoolExecutor
from abc import abstractmethod, ABC


class AbstractDeviceFactory(ABC):
    @abstractmethod
    def create_device(self, name, settings) -> AbstractRegistratorDriverAdapter:
        pass


class DefaultDeviceFactory(AbstractDeviceFactory):
    def __init__(self, loop):
        self._loop = loop

    def create_device(self, device_adapter_name, settings) -> AbstractRegistratorDriverAdapter:
        shift_duration = settings.pop('shift_duration')
        general_adapter = DefaultModuleLoader().load('hardware.adapters', device_adapter_name, **settings)
        async_decorator = AsyncRegistrator(general_adapter, DefaultStateFactory(shift_duration), self._loop,
                                           AsyncTreadPoolExecutor(self._loop))

        return async_decorator


