from receipt.domain.receipt import *
from receipt.domain.payments import PaymentFactory
from receipt.domain.products import CommodityFactory
from test.receipt.domain import test_products
from collections import namedtuple
import random
import datetime


class TestAuxiliaryObjects:
    # Тест вспомогательных объектов
    def test_email(self):
        email_data = {'ivan@mail.ru': True, 'kot@sobaka.ru': True, 'some.n_am-e@mail.ru': True, 'ivan@dorn': False,
                      'email': False}

        for addr, expected_result in email_data.items():
            try:
                email = Email(addr)
                assert email.get_value() == addr, 'Несоответствие эл. почты {} {}'.format(addr, email.get_value())
                fact_result = True
            except ValueError:
                fact_result = False
            assert fact_result == expected_result, 'Неправильно обработан адрес {}'.format(addr)

    def test_phone_number(self):
        original_phone = '79652156554'
        phone_data = {'ivan@mail.ru': False, '+79652156554': True, '20548987886544600446544655464': False,
                      '+7(965)2156554': True, '+7-965-215-65-54': True}

        for income_value, expected_result in phone_data.items():
            try:
                number = PhoneNumber(income_value)
                assert number.get_value() == original_phone, \
                    'Несоответствие телефонного номера {} {}'.format(original_phone, number.get_value())
                fact_result = True
                number.__repr__()
            except ValueError:
                fact_result = False
            assert fact_result == expected_result, 'Неправильно обработано значение {}'.format(income_value)

    def test_cashier(self):
        Rec = namedtuple('Rec', ('name', 'inn', 'result'))
        cashier_data = (Rec('Иванов Иван Иванович', '234324234245', True),
                        Rec('Петров Иван Иванович', None, True),
                        Rec('Сидоров Иван Иванович', '234234234234234324324324324324', False),
                        Rec('Новиков Иван Иванович', 'ИванИвановИв', False))

        for data in cashier_data:
            try:
                cashier = Cashier(data.name, data.inn)
                assert data.result is True, 'Неправильно обработано значение {}'.format(str(data))
                cashier.__repr__()
                assert data.inn == cashier.inn, 'Несоответсвие ИНН'.format(cashier)
                assert data.name == cashier.name, 'Несоответсвие Имени кассира {}'.format(cashier)
            except ValueError:
                assert data.result is False, 'Неправильно обработано значение {}'.format(str(data))

    def test_correction_data_classes(self):
        symbols = [str(i) for i in range(0,10)]
        Item = namedtuple('Item', ['cls', 'symbol_limit'])
        items = (Item(CorrectionReason, 256), Item(MistakenReceiptNumber, 16), Item(CorrectionDocumentNumber,  32))
        for item in items:
            valid_value = ''.join(random.choices(symbols, k=item.symbol_limit))
            obj = item.cls(valid_value)
            assert_msg = 'Несоответствие значений. Объект класса {}. Искомое {}, Возвращаемое методом {}'
            assert obj.get_value() == valid_value,assert_msg.format(item.cls, valid_value, obj.get_value())
            assert valid_value == str(obj)
            invalid_value = ''.join(random.choices(symbols, k=item.symbol_limit+1))
            try:
                invalid_obj = item.cls(invalid_value)
                assert_msg = 'Объект класса {} не должен был создан из невалидного значения длиной {} символов'
                assert False, assert_msg.format(item.cls, len(invalid_value))
            except ValueError:
                pass

        reason_str = 'Причина коррекции'
        doc_date = datetime.date.today()
        doc_number_str = '55654'
        correction_data =  CorrectionData(CorrectionReason(reason_str), doc_date,
                                          CorrectionDocumentNumber(doc_number_str), precept=True)

        # Проверим доступность атрибутов корректирующих данных
        assert correction_data.correction_doc_number.get_value() == doc_number_str
        assert correction_data.correction_reason.get_value() == reason_str
        assert correction_data.correction_date == doc_date
        assert correction_data.precept is True


class TestReceipt:
    def test_buy_receipt(self):
        user_id = 5
        r1192 = '5443234234'  # Реквизит, применяемый для корректировок, содержит номер корректируемого документа
        order_id = 5050
        receipt = Sell(user_id, order_id, MistakenReceiptNumber(r1192))
        receipt.email = Email('test@example.ru')
        # Добавляем продукты и услуги в чек
        products_data = test_products.get_income_data()
        commodity_factory = CommodityFactory()
        for item in products_data:
            receipt.add_commodity(commodity_factory.get_commodity(*item))

        total_price = receipt.get_commodities_total_cost()

        # Добавим платежи
        payment_factory = PaymentFactory()
        cash_payment_id = 0
        card_payment_id = 1
        receipt.add_payment(payment_factory.get_payment(cash_payment_id, total_price / 2))
        receipt.add_payment(payment_factory.get_payment(card_payment_id, total_price / 2))

        assert total_price == receipt.get_payments_total()

        # Валидация
        err_handler = MockErrorHandler()
        validator = ReceiptDefaultValidator(err_handler)
        receipt.set_validator(validator)
        assert receipt.is_valid, str(err_handler)

        receipt.add_payment(payment_factory.get_payment(cash_payment_id, total_price / 2))
        assert not receipt.is_valid

