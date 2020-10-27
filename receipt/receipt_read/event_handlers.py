from core.events.events import AbstractEventHandler
from core.events import AbstractEventDispatcher
from receipt.events import ReceiptRegistered, ReceiptCreated, ReceiptRegistationFailed
from receipt.registrator_info_storages import AbstractRegistratorDataStorage
from logging import getLogger


logger = getLogger(__name__)


class ReceiptCreatedHandler(AbstractEventHandler):
    def __init__(self, receipt_read_repository):
        self._repository = receipt_read_repository

    def subscribe(self, event_dispatcher: AbstractEventDispatcher):
        event_dispatcher.add_subscriber(ReceiptCreated, self)

    async def handle(self, event: ReceiptCreated):
        logger.debug('ReceiptCreated event handled')
        await self._repository.save(event.data)


class ReceiptReceiptRegistationFailedHandler(AbstractEventHandler):
    def __init__(self, receipt_read_repository):
        self._repository = receipt_read_repository

    def subscribe(self, event_dispatcher: AbstractEventDispatcher):
        event_dispatcher.add_subscriber(ReceiptRegistationFailed, self)

    async def handle(self, event: ReceiptRegistationFailed):
        logger.debug('ReceiptRegistationFailed event handled')
        await self._repository.update(event.data)


class ReceiptReceiptRegisteredHandler(AbstractEventHandler):
    def __init__(self, receipt_read_repository, registrator_data_storage: AbstractRegistratorDataStorage):
        self._repository = receipt_read_repository
        self._registrator_data_storage = registrator_data_storage

    def subscribe(self, event_dispatcher: AbstractEventDispatcher):
        event_dispatcher.add_subscriber(ReceiptRegistered, self)

    async def handle(self, event: ReceiptRegistered):
        logger.debug('ReceiptRegistered event handled')
        data = (await self._registrator_data_storage.get(event.data['registrator_id']))
        data = data.as_dict()
        data.update(event.data)
        data['id'] = event.entity_id
        await self._repository.update(data)