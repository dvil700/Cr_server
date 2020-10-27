import pytest
from receipt.serializers import ReceiptSerializer


class TestForms:
    def test_one(self):
        data = {'email': 'dvil@mail.ru',
                'products': [
                    {'name': 'Поилка ниппельная', 'payment_state_int': 1, 'price': 100, 'commodity_type_int': 1,
                     'quantity': 1.0},
                    {'name': 'Организация доставки товара', 'payment_state_int': 1, 'commodity_type_int': 4,
                     'price': 100, 'quantity': 1.0}],
                'receiptType': 1, 'payments': [{'payment_type_int': 1, 'payment_sum': 200}]}
        form = ReceiptSerializer.from_json(data)
        assert form.validate()

