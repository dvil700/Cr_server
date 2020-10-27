from abc import ABC, abstractmethod
import decimal


class CommodityPaymentState(ABC):  # признак расчета за предмет расчета (товар, услугу) в чеке
    @abstractmethod
    def get_value(self) -> int:
        pass


class CommodityFullPrepayment(CommodityPaymentState):  # Предоплата 100%
    def get_value(self):
        return 1


class CommodityPrepayment(CommodityPaymentState):  # Предоплата (не полная)
    def get_value(self):
        return 2


class CommodityAdvance(CommodityPaymentState):  # Аванс
    def get_value(self):
        return 3


class CommodityFullPayment(CommodityPaymentState):  # Полный расчет
    def get_value(self):
        return 4


class CommodityName:  # наименование предмета расчета (товара, услуги и т.д.)
    def __init__(self, name: str):
        self._name = name

    def __str__(self):
        return self._name

    def __repr__(self):
        return self._name

    def get_value(self):
        return self._name


class Quantity:
    def __init__(self, value, precision: int, str_unit: str = None):
        # value - значение, precision - точность (знаков после запятой), str_unit - единицы изм. (шт., литры, тонны...)
        prec_str = '0.'
        for i in range(precision):
            prec_str = prec_str + '0'
        try:
            self._value = decimal.Decimal(value).quantize(decimal.Decimal(prec_str), rounding=decimal.ROUND_HALF_UP)
        except decimal.InvalidOperation:
            raise ValueError('Неверный тип значения количества')

        self._str_unit = str_unit
        self._precision = precision

    def __str__(self):
        unit_str = self._str_unit if self._str_unit else ''
        return '{} {}'.format(str(self._str_unit), unit_str).rstrip()

    def get_value(self) -> decimal.Decimal:
        return self._value

    def get_str_unit(self) -> str:
        return self._str_unit

    def get_precision(self) -> int:
        return self._precision


class Price:
    def __init__(self, price):
        try:
            self._value = decimal.Decimal(price).quantize(decimal.Decimal('0.01'), decimal.ROUND_HALF_UP)
        except decimal.InvalidOperation:
            raise ValueError('Неверный тип стоимости')

    def __str__(self):
        return str(self._value)

    def get_value(self) -> decimal.Decimal:
        return self._value


class CommodityTaxType(ABC):
    _value: int

    def get_value_int(self):
        return self._value


class TaxDepartment(CommodityTaxType):
    # тип, привязанный к секции товара
    _value = 0


class Tax18(CommodityTaxType):
    # НДС 18%
    _value = 1


class Tax10(CommodityTaxType):
    # НДС 10%
    _value = 2


class Tax118(CommodityTaxType):
    # НДС расчитанный 18/118
    _value = 3


class Tax110(CommodityTaxType):
    # НДС расчитанный 10/110
    _value = 4


class Tax0(CommodityTaxType):
    # НДС 0%
    _value = 5


class TaxNo(CommodityTaxType):
    # Без НДС
    _value = 6


class Tax20(CommodityTaxType):
    # НДС 20%
    _value = 7


class Tax120(CommodityTaxType):
    # НДС расчитанный 20/120
    _value = 8


class Commodity(ABC):  # предмет расчета. Наследниками будут товар, услуга и т.д.
    def __init__(self, name: CommodityName, quantity: Quantity, price: Price, payment_state: CommodityPaymentState,
                 tax_type: CommodityTaxType = None):
        self._name = name
        self._quantity = quantity
        self._price = price
        self._payment_state = payment_state
        self._tax_type = tax_type

    @abstractmethod
    def get_type_int(self) -> int:  # целочисленное представление типа предмета расчета (товара, услуги и т.д)
        pass

    @property
    def name(self):
        return self._name

    @property
    def quantity(self):
        return self._quantity

    @property
    def price(self):
        return self._price

    @property
    def payment_state(self):
        return self._payment_state

    def get_total_cost(self) -> decimal.Decimal:
        return (self.quantity.get_value() * self.price.get_value()).quantize(decimal.Decimal('.00'),
                                                                             rounding=decimal.ROUND_HALF_UP)

    @property
    def tax_type(self) -> CommodityTaxType:
        return self._tax_type

    def as_dict(self):
        return dict(name=str(self.name), quantity=self.quantity.get_value(), price=self.price.get_value(),
                    commodity_type_int=self.get_type_int(), payment_state_int=self.payment_state.get_value(),
                    quantity_prec = self.quantity.get_precision(), quantity_unit = self.quantity.get_str_unit(),
                    tax_type_int = self.tax_type.get_value_int())


class Product(Commodity):  # Предмет расчета - продукт
    def get_type_int(self):
        return 1


class Service(Commodity):  # Предмет расчета - услуга
    def get_type_int(self):
        return 4


class AbstractCommodityFactory(ABC):
    # Фабрика предметов расчета (товаров, услуг)
    def get_commodity(self, *args, **kwargs) -> Commodity:
        # На основе параметров возвращает подходящий объект товара, либо услуги
        pass


class CommodityFactory(AbstractCommodityFactory):
    _PaymentStateMap = {str(item.get_value()): item for item in (CommodityFullPrepayment(), CommodityPrepayment(),
                                                                 CommodityAdvance(), CommodityFullPayment())}
    _CommodityClsMap = {'1': Product, '4': Service}
    _taxTypeMap = {str(item.get_value_int()): item for item in (TaxDepartment(), Tax18(), Tax10(), Tax118(), Tax110(),
                                                                Tax0(), TaxNo(), Tax20(), Tax120())}

    def _create_prepayment_state(self, value):
        payment_state = self._PaymentStateMap.get(str(value), None)
        if payment_state:
            return payment_state
        raise ValueError('Статус оплаты с индексом {} не предусмотрен'.format(str(value)))

    def _create_tax_type(self, value):
        if value is None:
            return
        tax_type = self._taxTypeMap.get(str(value), None)
        if tax_type:
            return tax_type
        raise ValueError('Тип налога с индексом {} не предусмотрен'.format(str(value)))

    def get_commodity(self, name, quantity, price, commodity_type_int, payment_state_int, quantity_prec=0,
                      quantity_unit=None, tax_type_int=6):

        commodity_cls = self._CommodityClsMap.get(str(commodity_type_int), None)
        if not commodity_cls:
            raise ValueError('Тип чека с индексом {} не предусмотрен'.format(str(commodity_type_int)))
        return commodity_cls(CommodityName(name), Quantity(quantity, quantity_prec, quantity_unit), Price(price),
                             self._create_prepayment_state(payment_state_int), self._create_tax_type(tax_type_int))
