import datetime
from logging import getLogger
from core.commands import AbstractCommand, ExecutionFailedError
from .events import ReceiptRegistationFailed, ReceiptRegistered
from .domain.receipt import ReceiptRegistrationError


logger = getLogger(__name__)


class RegisterReceiptCommand(AbstractCommand):
    _priority = 5

    def __init__(self, receipt, event_distatcher):
        self.datetime = datetime.datetime.now()
        self._receipt = receipt
        self._event_dispatcher = event_distatcher

    async def execute(self, fiscal_machine):
        logger.debug('The command %s started executing on fiscal device %s, receipt_id %d', str(self),
                     str(fiscal_machine), self._receipt.id)
        try:
            await fiscal_machine.register_receipt(self._receipt)
        except ReceiptRegistrationError as e:
            await self._event_dispatcher.handle(ReceiptRegistationFailed(self._receipt))
            logger.error('ReceiptRegistrationError during execution %s, fiscal device %s, receipt_id %d: %s', str(self),
                         str(fiscal_machine), self._receipt.id, str(e))
            raise ExecutionFailedError
        except Exception as e:
            logger.error('Error during execution %s, fiscal device %s, receipt_id %d: %s', str(self),
                         str(fiscal_machine), self._receipt.id, str(e))
            await self._event_dispatcher.handle(ReceiptRegistationFailed(self._receipt))
            raise ExecutionFailedError

        await self._event_dispatcher.handle(ReceiptRegistered(self._receipt))
        logger.debug('The command %s executed on fiscal device %s, receipt_id %d', str(self),
                     str(fiscal_machine), self._receipt.id)