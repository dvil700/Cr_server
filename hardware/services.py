import asyncio
from abc import ABC, abstractmethod
from logging import getLogger
from receipt.registrator_info_storages import AbstractRegistratorDataStorage, RegistratorDataNotExists
from .factories import DefaultDeviceFactory
from .adapters import AbstractRegistratorDriverAdapter
from .adapters.info import PackInfo


logger = getLogger(__name__)


class AbstractAvailableDriversInformationService(ABC):
    @abstractmethod
    def get_available_drivers_list(self) -> list:
        pass


class AvailableDriversInformationService(AbstractAvailableDriversInformationService):
    def get_available_drivers_list(self):
        return PackInfo().get_available_adapters()


class DeviceCreationError(Exception):
    pass


class AbstractDeviceCreationService(ABC):
    @abstractmethod
    async def create_device(self, device_driver_name:str, config: dict) -> AbstractRegistratorDriverAdapter:
        # This method creates instances of AbstractRegistratorDriverAdapter type and it also must set
        # a id property value for each instance
        pass


class DefaultFiscalDeviceCreationService(AbstractDeviceCreationService):
    def __init__(self, loop: asyncio.AbstractEventLoop, registrator_data_storage: AbstractRegistratorDataStorage):
        self._device_factory = DefaultDeviceFactory(loop)
        self._loop = loop
        self._registrator_data_storage = registrator_data_storage

    async def create_device(self, device_driver_name: str, config: dict):
        try:
            device = await self._loop.run_in_executor(None, self._device_factory.create_device, device_driver_name,
                                                      config)
        except Exception as e:
            logger.error(str(e))
            raise DeviceCreationError
        registrator_info = await device.get_registrator_info()
        try:
            device.id = await self._registrator_data_storage.get_id(registrator_info)
        except RegistratorDataNotExists:
            device.id = await self._registrator_data_storage.add(registrator_info)
        return device

