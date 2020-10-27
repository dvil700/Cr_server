from hardware.fiscal_device_group_managers import DeviceGroupManager
from hardware.adapters import AbstractRegistratorDriverAdapter
import pytest
import asyncio
from mock import Mock, AsyncMock
from core.commands import AbstractCommand
import datetime

pytestmark = pytest.mark.asyncio


@pytest.fixture
def manager():
    return DeviceGroupManager('name', asyncio.get_event_loop())


class Command(AbstractCommand):
    _priority = 5

    def __init__(self):
        self.datetime = datetime.datetime.now()
    execute = AsyncMock()


class Device(AbstractRegistratorDriverAdapter):
    register_receipt = AsyncMock()
    close_shift = AsyncMock()
    open_shift = AsyncMock()
    set_date_time = AsyncMock()
    get_date_time = AsyncMock()
    get_shift_info = AsyncMock()
    get_registrator_info = AsyncMock()
    reboot = AsyncMock()
    close = AsyncMock()


@pytest.fixture()
def command():
    com = Command()
    return com


class TestDeviceGroupManager:
    def test_add(self, manager: DeviceGroupManager):
        service_group_id = 1
        device = Device()
        manager.add_device(service_group_id , device)

    async def test_proccess_command(self, manager: DeviceGroupManager, command):
        service_group_id = 1
        try:
            await manager.process_command(service_group_id, command)
        except KeyError:
            assert True

        device = Device()
        manager.add_device(service_group_id , device)
        await manager.process_command(service_group_id, command)
        await asyncio.sleep(0.1)
        assert command.execute.called

    async def test_replace_device(self, manager: DeviceGroupManager):
        service_group_id = 1
        device = Device()
        manager.add_device(service_group_id , device)
        device2 = Device()
        await manager.replace_device(service_group_id, device2)
        await manager.open_shift(service_group_id)
        assert device2.open_shift.called

    async def test_closing(self, manager: DeviceGroupManager):
        devices = []
        devices_count = 10
        for service_group_id in range(devices_count):
            device = Device()
            devices.append(device)
            manager.add_device(service_group_id , device)
            for i in range(100):
                await manager.process_command(service_group_id, Command())
        await manager.close()
        for service_group_id in range(devices_count):
            assert not manager.is_device_provided_for_group(service_group_id)

    async def test_other_methods(self, manager: DeviceGroupManager):
        service_group_id = 1
        device = Device()
        manager.add_device(service_group_id , device)
        await manager.open_shift(service_group_id)
        assert device.open_shift.called

        await manager.close_shift(service_group_id)
        assert device.close_shift.called

        await manager.get_shift_info(service_group_id)
        assert device.get_shift_info.called

        await manager.close_device(service_group_id)
        assert device.close.called

        await manager.reboot(service_group_id)
        assert device.reboot.called

        await manager.detach_device(service_group_id)
        assert not manager.is_device_provided_for_group(service_group_id)