import pytest
from mock import AsyncMock
from hardware.services import DefaultFiscalDeviceCreationService, AvailableDriversInformationService
from receipt.registrator_info_storages import AbstractRegistratorDataStorage


pytestmark = pytest.mark.asyncio


class MockRegistratorDataStorage():
    def __init__(self):
        self.get = AsyncMock()
        self.get_id = AsyncMock()
        self.add = AsyncMock()
        self.get_registrators_by_sn = AsyncMock()
        self.get_registrators_by_company_inn = AsyncMock()
        self.get_last_id = AsyncMock()


class TestDeviceCreation:
    async def test_device_creation(self, event_loop):
        service = DefaultFiscalDeviceCreationService(event_loop, MockRegistratorDataStorage())
        device = await service.create_device('test', {'shift_duration': 36000})
        from hardware.adapters.base import AbstractRegistratorDriverAdapter
        assert isinstance(device, AbstractRegistratorDriverAdapter)


class TestFiscalInformationService:
    def test_information_service(self):
        service = AvailableDriversInformationService()
        drivers_list = service.get_available_drivers_list()
        assert 'test' in drivers_list