from abc import ABC, abstractmethod
import decimal
import re
from .products import Commodity
from .payments import Payment
import datetime
from collections import namedtuple
import random


class TaxSystem(ABC):
    @abstractmethod
    def get_value_int(self) -> int:
        pass


class Osn(TaxSystem):
    # Общая система налогообложения
    def get_value_int(self) -> int:
        return 1


class UsnIncome(TaxSystem):
    # УСН Доход
    def get_value_int(self) -> int:
        return 2


class UsnDifference(TaxSystem):
    # УСН Доход-Расход
    def get_value_int(self) -> int:
        return 4


class Envd(TaxSystem):
    # ЕНВД
    def get_value_int(self) -> int:
        return 8


class Esn(TaxSystem):
    # ЕСН
    def get_value_int(self) -> int:
        return 16


class Patent(TaxSystem):
    # Патент
    def get_value_int(self) -> int:
        return 32


class Email:
    def __init__(self, email: str):
        if len(email) > 256:
            raise ValueError('Значение email должно быть не более 256 символов')

        if not re.match(r'^([\w_\.+]|-)+@.+\.([\w_\.+]|-)+$', email):
            raise ValueError('Значение email не является валидным')

        self._value = email

    def __str__(self):
        return self._value

    def __repr__(self):
        return self._value

    def get_value(self):
        return self._value


class PhoneNumber:
    def __init__(self, phone_number: str):
        phone_number = re.sub(r'(\+|\s|-|\(|\))', '', phone_number)

        if 10 < len(phone_number) > 20:
            raise ValueError('Количество цифр в phone_number должно быть не более 20 символов и не менее 10 символов')

        if not re.match(r'^\d{8,20}$', phone_number):
            raise ValueError('Значение телефонного номера не является валидным')

        self._value = phone_number

    def __str__(self):
        return self._value

    def __repr__(self):
        return self._value

    def get_value(self):
        return self._value


class Cashier:
    def __init__(self, name: str, inn: str = None):
        if len(name) > 64:
            raise ValueError('Значение имени кассира должно быть не более 64 символов')
        if inn and not re.match(r'^\d{12}$', inn):
            raise ValueError('Значение ИНН кассира должно быть 12 символов от 0 до 9')
        self._name = name
        self._inn = inn

    @property
    def name(self):
        return self._name

    @property
    def inn(self):
        return self._inn

    def __repr__(self):
        return ' '.join([self.__class__.__name__, self._name, 'inn:', str(self._inn)])

    def __str__(self):
        ' '.join([self._name, self._inn])

    def as_dict(self):
        return dict(name=self.name, inn=self.inn)


class MistakenReceiptNumber:
    # Фискальный признак документа неправильно пробитого, чека (реквизит 1192). Заполняется в случае если чек
    # регистрируется для исправления ранее зарегистрированного чека.
    def __init__(self, value: str):
        if len(value) > 16:
            raise ValueError('Значение номера неправильно пробитого чека должно быть не более 16 символов')
        self._value = value

    def __str__(self):
        return str(self._value)

    def get_value(self):
        return self._value


class CorrectionReason:
    # Основание коррекции - параметр 1177
    def __init__(self, value: str):
        if len(value) > 256:
            raise ValueError('Значение основания коррекции не должно быть не более 256 символов')
        self._value = value

    def get_value(self):
        return self._value

    def __repr__(self):
        return ' '.join([self.__class__.__name__, '(parameter 1177)', self._value])

    def __str__(self):
        return str(self._value)


class CorrectionDocumentNumber:
    # Номер предписания - параметр 1179
    def __init__(self, value: str):
        if len(value) > 32:
            raise ValueError('Значение номера предписания не должно не более 32 символов')
        self._value = value

    def get_value(self):
        return self._value

    def __repr__(self):
        return ' '.join([self.__class__.__name__, '(parameter 1179)', self._value])

    def __str__(self):
        return str(self._value)


class CorrectionData:
    def __init__(self, correction_reason: CorrectionReason, correction_date: datetime.date,
                 doc_number: CorrectionDocumentNumber = None, precept=False):
        self._correction_reason = correction_reason  # Основание для коррекции, 1177
        self._correction_date = correction_date  # 1178 дата коррекции
        self._correction_doc_number = doc_number if doc_number else None  # 1179 номер документа основания (предписания)
        self._precept = precept  # было ли предписание 1173

    @property
    def correction_reason(self) -> CorrectionReason:
        return self._correction_reason  # Реквизит 1177

    @property
    def correction_date(self) -> datetime.date:
        return self._correction_date

    @property
    def correction_doc_number(self) -> CorrectionDocumentNumber:
        return self._correction_doc_number

    @property
    def precept(self) -> bool:
        return self._precept

    def as_dict(self):
        return dict(correction_reason=str(self._correction_reason), correction_date=str(self.correction_date),
                    correction_doc_number=str(self._correction_doc_number))


class ReceiptRegistratorData:
    # Данные регистрирующего устройства (кассы): серийные номера, регистрационные данные, ОФД
    __slots__ = '_values', '_id'

    def __init__(self, registration_number: str, registrator_serial: str, fn_serial: str, ffd_version: str,
                 ofd_name: str, ffd_inn: str, company_name: str, company_inn: str, operations_address: str,
                 operations_place: str):
        Values = namedtuple('Values', ['registration_number', 'registrator_serial', 'fn_serial', 'ffd_version',
                                       'ofd_name', 'ffd_inn', 'company_name', 'company_inn', 'operations_address',
                                       'operations_place'])
        self._values = Values(registration_number, registrator_serial, fn_serial, ffd_version,
                              ofd_name, ffd_inn, company_name, company_inn, operations_address, operations_place)
        self._id = None

    def set_id(self, id: int):
        self._id = id

    @property
    def id(self):
        return self._id

    @property
    def registration_number(self):
        return self._values.registration_number

    @property
    def registrator_serial(self):
        return self._values.registrator_serial

    @property
    def fn_serial(self):
        return self._values.fn_serial

    @property
    def ffd_version(self):
        return self._values.ffd_version

    @property
    def ofd_name(self):
        return self._values.ofd_name

    @property
    def ffd_inn(self):
        return self._values.ffd_inn

    @property
    def company_name(self):
        return self._values.company_name

    @property
    def company_inn(self):
        return self._values.company_inn

    @property
    def operations_address(self):
        return self._values.operations_address

    @property
    def operations_place(self):
        return self._values.operations_place

    def __iter__(self):
        return iter(self._values)

    def __getitem__(self, key):
        return getattr(self._values, key)

    def items(self):
        for key in self._values._fields:
            yield key, getattr(self._values, key)

    def __hash__(self):
        return hash(self._values)

    def as_dict(self):
        return self._values._asdict()


class ReceiptValidatorABC(ABC):
    @abstractmethod
    def validate(self, receipt) -> bool:
        pass


class ValidationErrorHandler(ABC):
    @abstractmethod
    def handle_error(self, error_message: str):
        pass


class Receipt:  # чек ффд 105
    __slots__ = ('_id', '_order_id', '_user_id', '_service_id', '_mistaken_receipt_number', '_email', '_phone_number',
                 '_commodities', '_payments', '_commodities_total_cost', '_payments_total', '_validator', '_is_valid',
                 '_registrator_id', '_fiscal_sign', '_registration_datetime', '_cashier', '_shift_num', '_receipt_num',
                 '_receipt_in_shift_num', '_tax_system', '_correction_data', '_need_print', '_receipt_num')

    def __init__(self, user_id: int, service_id: int, order_id: int = None,
                 mistaken_receipt_number: MistakenReceiptNumber = None, need_print: bool = False):
        self._id = None
        self._order_id = order_id
        self._user_id = user_id
        self._service_id = service_id
        self._mistaken_receipt_number = mistaken_receipt_number  # реквизит 1192 Номер ошибочного чека
        # (заполняется в случае исправления ошибок в ранее произведенных расчетах
        self._email = None
        self._phone_number = None
        self._commodities = []
        self._payments = []
        self._commodities_total_cost = decimal.Decimal('0.00')
        self._payments_total = decimal.Decimal('0.00')
        self._validator = None
        self._is_valid = False
        self._registrator_id = None  # id кассового аппарата
        self._fiscal_sign = None  # фискальный признак документа
        self._registration_datetime = None
        self._cashier = None  # Кассир
        self._shift_num = None  # Номер смены
        self._receipt_in_shift_num = None  # номер документа в смене
        self._tax_system = None
        self._correction_data = None
        self._need_print = need_print  # печатать ли чек на бумаге
        self._receipt_num = None  # Номер документа в кассовом аппарате

    def set_validator(self, validator: ReceiptValidatorABC):
        self._validator = validator

    @abstractmethod
    def get_type_int(self) -> int:  # целочисленное представление типа чека (чек прихода, расхода, возврата и т.д)
        pass

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        if self._id:
            raise AttributeError('Attribute "id" has been already set')
        self._id = value

    @property
    def user_id(self):
        return self._user_id

    @property
    def service_id(self):
        return self._service_id

    @property
    def order_id(self):
        return self._order_id

    def add_commodity(self, commodity: Commodity):
        self._commodities_total_cost += commodity.get_total_cost()
        self._commodities.append(commodity)

    def add_payment(self, payment: Payment):
        self._payments_total += payment.get_value()
        self._payments.append(payment)

    @property
    def commodities(self):
        # Предметы расчета: товары, услуги
        for commodity in self._commodities:
            yield commodity

    @property
    def payments(self):
        for payment in self._payments:
            yield payment

    @property
    def mistaken_receipt_number(self):
        # Реквизит 1192. Номер исправляемого чека
        return self._mistaken_receipt_number

    @property
    def correction_data(self):
        # Данные корректировочного чека
        return self._correction_data

    @correction_data.setter
    def correction_data(self, value: CorrectionData):
        self._correction_data = value

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, email: Email):
        self._email = email

    @property
    def tax_system(self):
        # Система налогообложеия
        return self._tax_system

    @tax_system.setter
    def tax_system(self, tax_system: TaxSystem):
        self._tax_system = tax_system

    @property
    def phone_number(self):
        return self._phone_number

    @phone_number.setter
    def phone_number(self, phone_number: PhoneNumber):
        self._phone_number = phone_number

    @property
    def cashier(self):
        # Кассир
        return self._cashier

    @cashier.setter
    def cashier(self, cashier: Cashier):
        self._cashier = cashier

    def set_fiscal_data(self, fiscal_sign: str, registration_datetime: datetime.datetime, registrator_id: int,
                        shift_num: str, receipt_in_shift_num: str, receipt_number: str):
        # Метод устанавлиевает фискальные данные зарегистрированного чека
        self._fiscal_sign = fiscal_sign
        self._registration_datetime = registration_datetime
        self._registrator_id = registrator_id
        self._shift_num = shift_num
        self._receipt_in_shift_num = receipt_in_shift_num
        self._receipt_num = receipt_number

    @property
    def fiscal_sign(self):
        # Фискальный признак документа
        return self._fiscal_sign

    @property
    def registration_datetime(self):
        # Дата и время регистрации чека
        return self._registration_datetime

    @property
    def receipt_num(self):
        # Номер смены
        return self._receipt_num

    @property
    def shift_num(self):
        # Номер смены
        return self._shift_num

    @property
    def receipt_in_shift_num(self):
        # Порядковый номер документа в смене
        return self._receipt_in_shift_num

    def is_correcting(self):
        return False

    @property
    def registrator_id(self):
        return self._registrator_id

    def get_payments_total(self):
        # Общая суммма оплаты
        return self._payments_total

    def get_commodities_total_cost(self):
        # Общая стоимость товаров
        return self._commodities_total_cost

    @property
    def is_valid(self):
        self.validate()
        return self._is_valid

    def validate(self):
        if not self._validator:
            self._is_valid = True
            return
        self._is_valid = self._validator.validate(self)
        return self._is_valid

    @property
    def need_print(self) -> bool:
        # Нужно ли печатать бумажный чек
        return self._need_print

    def as_dict(self):
        return dict(id=self._id, order_id=self.order_id, user_id=self.user_id, service_id=self.service_id,
                    mistaken_receipt_number=str(self.mistaken_receipt_number), email=str(self.email),
                    phone_number=str(self.phone_number), registrator_id=self.registrator_id,
                    fiscal_sign=self.fiscal_sign, registration_datetime=self.registration_datetime,
                    cashier= self.cashier.as_dict() if self.cashier else None, shift_num=self.shift_num,
                    tax_system=self.tax_system,
                    correction_data=self.correction_data.as_dict() if self.correction_data else None,
                    receipt_in_shift_num=self.receipt_in_shift_num, need_print=self.need_print,
                    receipt_num=self.receipt_num, payments_total=self.get_payments_total(),
                    commodities_total_cost=self.get_commodities_total_cost(),
                    commodities=[item.as_dict() for item in self.commodities],
                    payments=[item.as_dict() for item in self.payments])


class Sell(Receipt):
    # Чек продажи
    def get_type_int(self):
        return 1


class SellReturn(Receipt):
    # Чек возврата продажи
    def get_type_int(self):
        return 2


class CorrectionReceipt(Receipt, ABC):
    def is_correcting(self):
        return True


class SellCorrection(CorrectionReceipt):
    # Чек коррекции продажи
    def get_type_int(self):
        return 7


class SellReturnCorrection(CorrectionReceipt):
    # Чек коррекции возврата продажи
    def get_type_int(self):
        return 8


class Buy(Receipt):
    # Чек расхода
    def get_type_int(self):
        return 4


class BuyReturn(Receipt):
    # Чек возврата расхода
    def get_type_int(self):
        return 5


class ByCorrection(CorrectionReceipt):
    # Чек коррекции расхода
    def get_type_int(self):
        return 9


class ByReturnCorrection(CorrectionReceipt):
    # Чек коррекции возврата расхода
    def get_type_int(self):
        return 10


class ReceiptDefaultValidator(ReceiptValidatorABC):
    def __init__(self, error_handler: ValidationErrorHandler):
        self._error_handler = error_handler

    def validate(self, receipt: Receipt):
        email_check = self._check_email_phone(receipt)
        totals_check = self._check_totals(receipt)
        return email_check * totals_check

    def _check_email_phone(self, receipt: Receipt):
        if receipt.email or receipt.phone_number:
            # Должно быть заполнено одно из полей
            self._error_handler.handle_error('Отсутствуют Email и номер телефона.')
        return bool(receipt.email or receipt.phone_number)

    def _check_totals(self, receipt):
        if receipt.get_payments_total() == receipt.get_commodities_total_cost():
            return True
        self._error_handler.handle_error('Сумма оплаты и сумма стоимостей товаров по чеку не совпадают')
        return False


class MockErrorHandler(ValidationErrorHandler):
    def __init__(self):
        self._errors = []

    def handle_error(self, error_message: str):
        self._errors.append(error_message)

    def has_errors(self):
        if len(self._errors):
            return True
        return False

    def __str__(self):
        return ', '.join(self._errors)


class ReceiptRegistrationError(Exception):
    pass


class AbstractReceiptRegistrator(ABC):
    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, device_id: int):
        self._id = device_id

    @abstractmethod
    def register_receipt(self, receipt):
        # регистрирует фискальную операцию и устанавливает фискальные данные в объект чека
        pass

    @abstractmethod
    def get_registrator_info(self) -> ReceiptRegistratorData:
        # Возращает данные регистрационные данные кассы
        pass


RECEIPT_TYPES_AVAILABLE = {'1': Sell, '2': SellReturn, '4': Buy, '5': BuyReturn, '7': SellCorrection,
                           '8': SellReturnCorrection, '9': ByCorrection, '10': ByReturnCorrection}

TAX_SYSTEMS_AVAILABLE = {'1': Osn, '2': UsnIncome, '4': UsnDifference, '8': Envd, '16': Esn, '32': Patent}
