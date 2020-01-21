import aiohttp
import asyncio
from datetime import datetime
import json


async def test():
    data = dict(
        login='anat', password='anat',
        command='register_sale', client_operation_id=3454,
        client_operation_datetime=datetime.now().timestamp(),
        email='ddnjjk@locald.ru',
        products=[{'name': 'Поилка', 'price': 40, 'quantity': 1.0, 'paymentObject': 1, 'paymentMethod': 1},
                  {'name': 'Поилка вакуумная', 'price': 40, 'quantity': 1.0, 'paymentObject': 1,
                   'paymentMethod': 1}],
        payments=[{'summ': 80, 'paymentType': 0}], total=80, receiptType=1
    )

    async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
        async with session.post('http://127.0.0.1:3080/cr2/cr_proccessing/register_sale.do', json=data) as res:
            text = await res.text()
            print(text)
            print(res.status)


asyncio.run(test())
