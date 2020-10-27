import pytest
from mock import Mock
from hardware.adapters.base import AsyncRegistrator, DefaultStateFactory, AsyncTreadPoolExecutor
from hardware.adapters.test.adapter import TestRegistrator as Registrator
from receipt.services import ReceiptCreationService
from receipt.commands import RegisterReceiptCommand
from hardware.fiscal_device_group_managers import DeviceGroupManager
from core.events.event_dispatchers import EventDispatcher
from core.events.event_storages import InMemoryEventStorage

pytestmark = pytest.mark.asyncio


data = {'email': 'dvil@mail.ru',
            'products': [{'name': 'Поилка ниппельная', 'payment_state_int': 1, 'price': 100, 'commodity_type_int': 1,
                          'quantity': 1.0},
                           {'name': 'Организация доставки товара', 'payment_state_int': 1, 'commodity_type_int': 4,
                            'price': 100, 'quantity': 1.0}],
          'receiptType': 1, 'payments': [{'payment_type_int': 1, 'payment_sum': 200}]}


class TestCommandExecution:
    async def test_adapter(self, event_loop):
        origin_adapter = Registrator()
        origin_adapter.id = 3
        receipt_factory = ReceiptCreationService()
        adapter = AsyncRegistrator(origin_adapter, DefaultStateFactory(3000), event_loop,
                                   AsyncTreadPoolExecutor(event_loop))
        receipt = receipt_factory.create_receipt(user_id=1, service_group_id=6, data=data)
        await adapter.register_receipt(receipt)

    async def test_with_commands(self, event_loop):
        origin_adapter = Registrator()
        origin_adapter.id = 3
        receipt_factory = ReceiptCreationService()
        adapter = AsyncRegistrator(origin_adapter, DefaultStateFactory(3000), event_loop,
                                   AsyncTreadPoolExecutor(event_loop))
        receipt = receipt_factory.create_receipt(user_id=1, service_group_id=6, data=data)

        command = RegisterReceiptCommand(receipt, EventDispatcher(InMemoryEventStorage()))
        await command.execute(adapter)



