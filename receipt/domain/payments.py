from abc import ABC, abstractmethod
import decimal


class Payment(ABC):
    def __init__(self, payment_sum):
        try:
            self._sum = decimal.Decimal(payment_sum).quantize(decimal.Decimal('0.01'), decimal.ROUND_HALF_UP)
        except decimal.InvalidOperation:
            raise ValueError('Неверный тип суммы оплаты')

    @abstractmethod
    def get_type_int(self) -> int:
        pass

    def get_value(self):
        return self._sum

    def __str__(self):
        return str(self._sum)

    def __repr__(self):
        return '{} {}'.format(self.__class__.__name__, self._sum)

    def as_dict(self):
        return dict(paymetn_sum=self.get_value(), payment_type_int=self.get_type_int())


class CashPayment(Payment):
    # Оплата по карте
    def get_type_int(self):
        return 0


class CardPayment(Payment):
    def get_type_int(self):
        return 1


class PrePayment(Payment):
    def get_type_int(self):
        return 2


class PaymentFactoryABC(ABC):
    @abstractmethod
    def get_payment(self, payment_type_int, sum):
        pass


class PaymentFactory(PaymentFactoryABC):
    _payments_map = {'0': CashPayment, '1': CardPayment, '2': PrePayment}

    def get_payment(self, payment_type_int, payment_sum):
        payment_cls = self._payments_map.get(str(payment_type_int), None)
        if not payment_cls:
            raise ValueError('Тип платежа с индексом {} не предусмотрен'.format(str(payment_type_int)))
        return payment_cls(payment_sum)
