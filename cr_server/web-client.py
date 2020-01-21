import aiohttp
import asyncio
import ssl
import json
from datetime import datetime


def get_make_data():
    cache=dict(i = 3454)
    def make_data():
        cache["i"]+=1
        return dict(
            username='vhshop', passwd='jQuery770771@',
            command='register_sale', client_operation_id=cache["i"],
            client_operation_datetime=datetime.now().timestamp(),
            email='ddnjjk@locald.ru',
            products=[{'name': 'Поилка', 'price': 40, 'quantity': 1.0, 'paymentObject': 1, 'paymentMethod': 1},
                      {'name': 'Поилка вакуумная', 'price': 40, 'quantity': 1.0, 'paymentObject': 1,
                       'paymentMethod': 1}],
            payments=[{'summ': 80, 'paymentType': 0}], total=80, receiptType=1)
    return make_data
async def arrange(loop):
    make_data=get_make_data()
    for _ in range(500):
        print('2')
        loop.create_task(req(make_data))
    await asyncio.sleep(0)
async def req(make_data):
    url = 'http://192.168.43.111:4080/cr_proccessing/proccess'
    url = 'http://127.0.0.1:3080/cr_proccessing/proccess'
    url = 'http://2.92.107.15:2080/cr_proccessing/proccess'
    # newdata=json.dumps(make_data())
    # header=make_headers(str(len(newdata)))
    headers = {'Content-type': 'application/json'}
    data = make_data()

    newdata = json.dumps(data)
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=newdata) as r:
            jsdata = await r.text()
            print(r.headers)
            print(r.status)
            print(jsdata)
            print(json.loads(jsdata))


loop = asyncio.get_event_loop()
loop.create_task(arrange(loop))
loop.run_forever()
# loop.create_task(req(mo))
# loop.run_forever()
