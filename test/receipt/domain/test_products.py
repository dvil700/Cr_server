import pytest
from receipt.domain.products import *
import decimal


def get_income_data():
    full_prepayment = 1
    product_int = 1
    service_int = 4
    # name, quantity, price, commodity_type_int, payment_state_int
    return [('Чайник', 1, 500, product_int, full_prepayment),
                   ('Доставка', 1, 200, service_int, full_prepayment)]


class TestAuxiliaryObjects:  # Тест вспомогательных объектов
    def test_payment_states(self):
        # Cтатусы оплаты товара
        payment_state_classes = (None, CommodityFullPrepayment, CommodityPrepayment, CommodityAdvance,
                                 CommodityFullPayment)

        for i, cls in enumerate(payment_state_classes):
            if i == 0: continue
            assert i == cls().get_value()

    def test_quantity(self):
        value = 5
        prec = 2
        unit = 'шт'
        quantity = Quantity(value, prec, unit)
        assert quantity.get_value() == decimal.Decimal(value).quantize(decimal.Decimal('.00'), decimal.ROUND_HALF_UP)
        assert quantity.get_str_unit() == unit

    def test_price(self):
        value = 50.55
        price = Price(value)
        assert price.get_value() == decimal.Decimal(value).quantize(decimal.Decimal('.00'), decimal.ROUND_HALF_UP)

    def test_name(self):
        name = 'Чайник'
        name_object = CommodityName('Чайник')
        assert name_object.get_value() == name


class TestProduct:
    def test_product(self):
        product = Product(CommodityName('Чайник'), Quantity(1, 0, 'шт'), Price(1300.00), CommodityFullPayment())
        service = Service(CommodityName('Доставка'), Quantity(1, 0), Price(500.00), CommodityFullPayment())
        assert type(product.name) == CommodityName
        assert type(product.quantity) == Quantity
        assert type(product.price) == Price
        assert isinstance(product.payment_state, CommodityPaymentState)
        assert product.get_total_cost() == decimal.Decimal('1')*decimal.Decimal('1300')



    def test_factory(self):
        income_data = get_income_data()
        commodities = [CommodityFactory().get_commodity(*item) for item in income_data]
        for i, commodity in enumerate(commodities):
            assert income_data[i] == (commodity.name.get_value(), commodity.quantity.get_value(),
                                      commodity.price.get_value(), commodity.get_type_int(),
                                      commodity.payment_state.get_value())







