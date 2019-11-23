import pytest
import asyncio
from config import CR_CONFIG
from drivers.atol10_adapter import Atl_cash_register


pytestmark=pytest.mark.asyncio

@pytest.yield_fixture
async def driver(event_loop):
    cash_register=Atl_cash_register(**CR_CONFIG, loop=event_loop)
    await  asyncio.sleep(5, event_loop)
    try:
        yield cash_register
    finally:
        await cash_register.close()
        
        
class TestCR:
    '''
    async def test_first(self, driver, event_loop):
        data= dict(email='ddnjjk@locald.ru',
                   products=[{'name': 'Поилка', 'price': 40, 'quantity': 1.0, 'paymentObject':1, 'paymentMethod':1},
                             {'name': 'Поилка вакуумная', 'price': 40, 'quantity': 1.0, 'paymentObject':1, 'paymentMethod':1}],
                   payments=[{'summ':80, 'payment_type':0}], total=80, receiptType=1,
                   operator = {'name':'Ильяшенко Дмитрий Владимирович', 'inn':'344405326900'}, is_electronary = False,
                   r1192 = None, test_mode = True)
        try:
            result = await driver.register_operation(*data.values())
            assert result==0, result
        except Exception as e:
            driver.driver.cancelReceipt()
            assert False, e
         '''

    async def test_get_cr_data(self, driver, event_loop):
        try:
            result = await driver.get_cr_data()
            print(result)
            assert result==0, result
        except Exception as e:
            driver.driver.cancelReceipt()
            assert False, e



         
 