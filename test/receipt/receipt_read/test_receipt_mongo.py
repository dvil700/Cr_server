import pytest
import motor.motor_asyncio
from receipt.receipt_read.repositories import MongoMotorReceiptRepository

pytestmark = pytest.mark.asyncio


class Test_mongo:
    async def test_repo(self):
        client = motor.motor_asyncio.AsyncIOMotorClient('localhost', 27017)
        db = client.test
        repo = MongoMotorReceiptRepository(db)
        receipt_id = await repo.get_last_id()
        company_id = 10
        income_data = {'id': receipt_id, 'company_id':company_id,'email':'dvil@mail.ru', 'state':'success'}
        await repo.save(income_data)
        result = await repo.get(receipt_id, company_id)
        income_data['_id'] = income_data.pop('id')
        assert income_data == result


