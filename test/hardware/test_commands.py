import pytest
import asyncio
from receipt import AbstractReceiptRegistrator
from receipt.events import ReceiptRegistered, ReceiptRegistationFailed
from receipt.commands import  RegisterReceiptCommand
from hardware.fiscal_device_group_managers import Invoker
from mock import Mock,  AsyncMock


pytestmark = pytest.mark.asyncio


class MockReceiptRegistrator(AbstractReceiptRegistrator):
    def __init__(self):
        self.register_receipt = AsyncMock()
        self.get_registrator_info = AsyncMock()

    @property
    def id(self):
        return 5

    def register_receipt(self, receipt):
        pass

    def get_registrator_info(self):
        pass


class TestCommands:
    async def test_register_receipt_command(self):
        invoker = Invoker(MockReceiptRegistrator(), asyncio.get_event_loop())
        event_dispatcher = Mock()
        receipt = Mock()
        command = RegisterReceiptCommand(receipt, event_dispatcher)
        invoker.put(command)
        await invoker.current_task
        assert ReceiptRegistered in map(type, event_dispatcher.handle.call_args.args)

        async def mock_method(*args, **kwargs):
            raise Exception
        # подменим метод регистрации чека, чтобы выбрасывалось исключение, и команда передавала в event_dispatcher
        # ReceiptRegistationFailed событие
        invoker.fr_adapter.register_receipt = mock_method

        invoker.put(command)
        await invoker.current_task
        assert ReceiptRegistationFailed in map(type, event_dispatcher.handle.call_args.args)