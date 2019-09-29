import pytest
import asyncio
from config import CR_CONFIG
from drivers.atol10_adapter import Atl_cash_register


pytestmark=pytest.mark.asyncio

@pytest.yield_fixture
async def connect_to_driver(event_loop):
    cash_register=Atl_cash_register(**CR_CONFIG, loop=event_loop)
    try:
        yield cash_register
    finally:
        await cash_register.close()
        
        
class TestCR:
    async def test_first(self, connect_to_driver, event_loop):
        driver= connect_to_driver
        data= dict(email='ddnjjk@locald.ru',
                   products=[{'name': 'Поилка', 'price': 40, 'quantity': 1.0, 'paymentObject':1, 'paymentMethod':1},
                             {'name': 'Поилка вакуумная', 'price': 40, 'quantity': 1.0, 'paymentObject':1, 'paymentMethod':1}],
                   payments=[{'summ':80, 'payment_type':0}], total=80, receiptType=1,
                   operator = None, is_electronary = True, r1192 = None, test_mode = True)

        result = await driver.register_operation(*data.values())


         
 