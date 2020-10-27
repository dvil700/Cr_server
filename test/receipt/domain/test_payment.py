import pytest
from receipt.domain.payments import CashPayment, CardPayment, PrePayment, PaymentFactory
import decimal


class TestPayment:
    def test_payment_classes(self):
        values = (500, 30.77, '50.44')
        value = values.__iter__()
        payments = [CashPayment(next(value)),
                    CardPayment(next(value)),
                    PrePayment(next(value))]

        decimal_values = [decimal.Decimal(item).quantize(decimal.Decimal('.00')) for item in values]
        payments_values = [item.get_value() for item in payments]
        assert decimal_values == payments_values

        int_types = [item.get_type_int() for item in payments]
        assert int_types == [0, 1, 2]

    def test_payment_factory(self):
        payment_factory = PaymentFactory()
        payments = [payment_factory.get_payment(i, 300+i) for i in range(3)]
        cls_tuple = (CashPayment, CardPayment, PrePayment)

        for i, payment in enumerate(payments):
            assert type(payment) == cls_tuple[i]
            value = decimal.Decimal(300+i).quantize(decimal.Decimal('.00'), decimal.ROUND_HALF_UP)
            assert value == payment.get_value()





