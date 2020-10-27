from abc import ABC, abstractmethod
from hardware import CommandProcessorInterface
from core.events import AbstractEventDispatcher
from . import Receipt
from .domain import get_default_receipt_factory
from .commands import RegisterReceiptCommand


class AbstractReceiptCreationService(ABC):
    @abstractmethod
    def create_receipt(self, user_id, service_group_id, data: dict):
        pass


class ReceiptCreationService:
    def __init__(self):
        self._factory = get_default_receipt_factory()

    def create_receipt(self, user_id, service_group_id, data: dict):
        return self._factory.create_receipt(user_id, service_group_id, data)


class AbstractReceiptProcessingService(ABC):
    @abstractmethod
    async def proccess(self, receipt: Receipt):
        pass

    @abstractmethod
    def is_service_provided(self, service_group_id):
        pass


class ReceiptProcessingService(AbstractReceiptProcessingService):
    def __init__(self, device_manager: CommandProcessorInterface, event_dispatcher: AbstractEventDispatcher):
        self._event_dispatcher = event_dispatcher
        self._device_manager = device_manager

    def _create_command(self, receipt):
        return RegisterReceiptCommand(receipt, self._event_dispatcher)

    async def proccess(self, receipt):
        command = self._create_command(receipt)
        await self._device_manager.process_command(receipt.service_id, command)

    def is_service_provided(self, service_group_id):
        return self._device_manager.is_device_provided_for_group(service_group_id)






