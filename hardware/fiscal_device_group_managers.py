from abc import ABC, abstractmethod
import asyncio
from .adapters import ShiftInformation, AbstractRegistratorDriverAdapter
from core.commands import AbstractInvoker, AbstractCommand
from logging import getLogger

logger = getLogger(__name__)


class DeviceIsRunning(Exception):
    pass


class DeviceIsNotRunning(Exception):
    pass


class DeviceIsNotAttached(Exception):
    pass


class DeviceAvailabilityCheck(ABC):
    @abstractmethod
    def is_device_provided_for_group(self, service_group_id):
        pass


class CommandProcessorInterface(ABC):
    @abstractmethod
    def process_command(self, service_group_id, command: AbstractCommand):
        pass


class AbstractDeviceGroupManager(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def add_device(self, service_group_id, device_adapter):
        pass

    @abstractmethod
    async def replace_device(self, service_group_id, device_adapter: AbstractRegistratorDriverAdapter):
        pass

    @abstractmethod
    async def open_shift(self, service_group_id):
        pass

    @abstractmethod
    async def close_shift(self, service_group_id):
        pass

    @abstractmethod
    async def get_shift_info(self, service_group_id) -> ShiftInformation:
        pass

    @abstractmethod
    async def close_device(self, service_group_id):
        pass

    @abstractmethod
    async def pause_command_execution(self, service_group_id):
        pass

    @abstractmethod
    async def resume_command_execution(self, service_group_id):
        pass

    @abstractmethod
    async def reboot(self, service_group_id):
        pass

    @abstractmethod
    async def detach_device(self, service_group_id):
        pass

    @abstractmethod
    async def close(self):
        pass


class Invoker(AbstractInvoker):
    # реализует очередь с приоритетами для команд и обеспечивает их последовательное исполнение
    def __init__(self, fr_adapter, loop):
        self._commands_queue = asyncio.PriorityQueue()
        self.lock = asyncio.Lock()
        self.loop = loop
        self._fr_adapter = fr_adapter
        self.current_task = None

    @property
    def fr_adapter(self):
        return self._fr_adapter

    async def set_fr_adapter(self, fr_adapter):
        async with self.lock:
            self._fr_adapter = fr_adapter

    async def pause(self):
        await self.lock.acquire()

    def resume(self):
        self.lock.release()

    async def _execute(self):
        async with self.lock:
            command = await self._commands_queue.get()
            try:
                await command.execute(self.fr_adapter)
            except Exception as e:
                logger.error(str(e))
            self._commands_queue.task_done()

        if self._commands_queue.qsize() > 0:
            self.current_task = self.loop.create_task(self._execute())

    def put(self, command: AbstractCommand):
        self._commands_queue.put_nowait(command)
        if self._commands_queue.qsize() == 1:
            self.current_task = self.loop.create_task(self._execute())

    def __str__(self):
        return self._commands_queue.__str__()

    async def wait_all_executed(self):
        await self._commands_queue.join()


class DeviceGroupManager(AbstractDeviceGroupManager, CommandProcessorInterface, DeviceAvailabilityCheck):
    def __init__(self, name, loop):
        self._name = name
        self._invokers = {}
        self._fiscal_devices = {}
        self._loop = loop

    @property
    def name(self):
        return self._name.lower()

    def _invoker_factory(self, device):
        return Invoker(device, self._loop)

    def add_device(self, service_group_id, device_adapter: AbstractRegistratorDriverAdapter):
        if self._fiscal_devices.get(service_group_id, None):
            raise DeviceIsRunning('The device with group id {} has been already provided'.format(service_group_id))
        self._fiscal_devices[service_group_id] = device_adapter
        self._invokers[service_group_id] = self._invoker_factory(device_adapter)

    async def replace_device(self, service_group_id, device_adapter):
        await self._invokers[service_group_id].set_fr_adapter(device_adapter)
        old_adapter = self._fiscal_devices[service_group_id]
        self._fiscal_devices[service_group_id] = device_adapter
        await old_adapter.close()

    async def process_command(self, service_group_id, command):
        self._invokers[service_group_id].put(command)

    async def open_shift(self, service_group_id):
        await self._fiscal_devices[service_group_id].open_shift()

    async def close_shift(self, service_group_id):
        await self._fiscal_devices[service_group_id].close_shift()

    async def get_shift_info(self, service_group_id) -> ShiftInformation:
        return await self._fiscal_devices[service_group_id].get_shift_info()

    async def close_device(self, service_group_id):
        await self._fiscal_devices[service_group_id].close()

    async def pause_command_execution(self, service_group_id):
        await self._invokers[service_group_id].pause()

    async def resume_command_execution(self, service_group_id):
        await self._invokers[service_group_id].resume()

    async def reboot(self, service_group_id):
        await self._fiscal_devices[service_group_id].reboot()

    async def detach_device(self, service_group_id):
        try:
            adapter = self._fiscal_devices.pop(service_group_id)
        except KeyError:
            raise DeviceIsNotAttached('There is not a fiscal device adapter attached to service group {}'. \
                                      format(service_group_id))
        invoker = self._invokers.pop(service_group_id)
        await invoker.wait_all_executed()
        await adapter.close()

    def is_device_provided_for_group(self, service_group_id):
        return self._fiscal_devices.get(service_group_id, False)

    async def close(self):
        for gr_id in list(self._fiscal_devices.keys()):
            await self.detach_device(gr_id)
