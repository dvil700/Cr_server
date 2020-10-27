from hardware.adapters.atol.adapter import AtlCashRegister
from hardware.adapters.atol import Loader
from hardware.adapters.base import DefaultTimeCounter
from receipt import get_default_receipt_factory


def get_receipt():
    data = {'email': 'dvil@mail.ru',
            'products': [{'name': 'Поилка ниппельная', 'payment_state_int': 1, 'price': 100, 'commodity_type_int': 1,
                          'quantity': 1.0},
                           {'name': 'Организация доставки товара', 'payment_state_int': 1, 'commodity_type_int': 4,
                            'price': 100, 'quantity': 1.0}],
          'receiptType': 1, 'payments': [{'payment_type_int': 1, 'payment_sum': 200}]}

    return get_default_receipt_factory().create_receipt(5, 10, data)


class TestAtolAdapter:
    def test_first(self):
        CR_CONFIG = {'cr_model': '57', 'cr_port': '1', 'cr_ofd_channel': '2', 'cr_baudrate': '115200',
                     'cr_passwd': '30'}

        driver_object = Loader().get_driver(**CR_CONFIG)
        driver_object.isOpened = lambda: 1
        driver_object.checkDocumentClosed = lambda: 1
        driver_object.openReceipt = lambda: 1
        driver_object.registration = lambda: 1
        driver_object.payment = lambda: 1
        driver_object.receiptTotal = lambda: 1

        cash_reg = AtlCashRegister(driver_object, DefaultTimeCounter(), test_mode=True)
        receipt = get_receipt()
        cash_reg.register_receipt(receipt)