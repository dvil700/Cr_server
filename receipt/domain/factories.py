from abc import ABC, abstractmethod
from .receipt import (RECEIPT_TYPES_AVAILABLE, TAX_SYSTEMS_AVAILABLE, Email, MistakenReceiptNumber, PhoneNumber,
                      CorrectionReason, CorrectionDocumentNumber, CorrectionData, Cashier, Receipt)
from .payments import PaymentFactoryABC, PaymentFactory
from .products import AbstractCommodityFactory, CommodityFactory


class AbstractReceiptFromDictFactory(ABC):
    @abstractmethod
    def create_receipt(self, user_id, client_id, income_data: dict) -> Receipt:
        pass


class ReceiptFromDictFactory(AbstractReceiptFromDictFactory):
    _receipt_map = RECEIPT_TYPES_AVAILABLE
    _tax_system_map = {key:item() for key, item in TAX_SYSTEMS_AVAILABLE.items()}

    def __init__(self, commodity_factory: AbstractCommodityFactory, payment_factory: PaymentFactoryABC):
        self._commodity_factory = commodity_factory
        self._payment_factory = payment_factory

    def create_receipt(self, user_id, client_id, data: dict):
        receipt_cls = self._receipt_map.get(str(data['receiptType']), None)
        if receipt_cls is None:
            raise ValueError('Тип чека с индексом {} не предусмотрен'.format(data['receiptType']))
        r1192 = data.get('mistaken_receipt_number', None)
        if r1192:
            r1192 = MistakenReceiptNumber(r1192)
        receipt = receipt_cls(user_id, client_id, data.get('order_id', None), r1192)
        receipt.id = data.get('id', None)
        self._set_commodities(receipt, data)
        self._set_payments(receipt, data)
        self._set_tax_system(receipt, data)
        self._set_email(receipt, data)
        self._set_phone_number(receipt, data)
        self._set_correction_data(receipt, data)
        return receipt

    def _set_correction_data(self, receipt, data):
        if not receipt.is_correcting():
            return
        if not data.get('correction_reason', None):
            raise ValueError('Отсутствует причина корректировки, correction_reason')
        if not data.get('correction_date', None):
            raise ValueError('Отсутствует дата за которую необходимо произвести коррекцию')
        correction_reason = CorrectionReason(data.get('correction_reason'))
        correction_date = data.get('correction_date')
        doc_number = CorrectionDocumentNumber(data.get('doc_number', None))
        precept = data.get('percept', False)
        receipt.set_correction_data(CorrectionData(correction_reason, correction_date, doc_number, precept))

    def _set_cashier(self, receipt, data):
        cashier = data.get('cashier', None)
        if cashier:
            receipt.cashier = Cashier(cashier['name'], cashier['inn'])

    def _set_tax_system(self, receipt, data):
        if data.get('tax_system', None):
            receipt.tax_system = self._tax_system_map[(data['tax_system'])]
            if receipt.tax_system is None:
                msg = 'Системы налогообложения соответствующей значению tax_system = {} не предусмотрено'
                raise ValueError(msg.format(data['tax_system']))

    def _set_email(self, receipt, data):
        if data.get('email', None):
            receipt.email = Email(data['email'])

    def _set_phone_number(self, receipt, data):
        if data.get('phone_number', None):
            receipt.phone_number = PhoneNumber(data['phone_number'])

    def _set_commodities(self, receipt, data):
        for i, product_dict in enumerate(data['products']):
            try:
                receipt.add_commodity(self._commodity_factory.get_commodity(**product_dict))
            except ValueError as error:
                raise ValueError('Ошибка в продукте с порядковым номером {}. {}'.format(i, error))

    def _set_payments(self, receipt, data):
        for i, payment_dict in enumerate(data['payments']):
            try:
                receipt.add_payment(self._payment_factory.get_payment(**payment_dict))
            except ValueError as error:
                raise ValueError('Ошибка в платеже с порядковым номером {}. {}'.format(i, error))


def get_default_receipt_factory() -> ReceiptFromDictFactory:
    return ReceiptFromDictFactory(CommodityFactory(), PaymentFactory())