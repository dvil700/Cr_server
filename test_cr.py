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
        await asyncio.sleep(5, loop=event_loop)
         
         
 