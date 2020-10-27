from wtforms import (Form, IntegerField, FormField, FieldList, StringField, DecimalField, DateField, validators,
                     BooleanField)
from wtforms.fields.html5 import EmailField

import wtforms_json
wtforms_json.init()


class ProductForm(Form):
    name = StringField(validators=[validators.DataRequired()])
    quantity = DecimalField(validators=[validators.DataRequired()])
    price = DecimalField(validators=[validators.DataRequired()])
    commodity_type_int = IntegerField(validators=[validators.DataRequired()])
    payment_state_int = IntegerField(validators=[validators.DataRequired()])
    quantity_prec = IntegerField(default=0)
    quantity_unit = StringField(default=None)
    tax_type_int = IntegerField(default=6)


class PaymentForm(Form):
    payment_type_int = IntegerField()
    payment_sum = DecimalField()


class ReceiptSerializer(Form):
    receiptType = IntegerField(validators=[validators.DataRequired()])
    mistaken_receipt_number = StringField(default=None)
    order_id = StringField()
    products = FieldList(FormField(ProductForm), validators=[validators.DataRequired()])
    payments = FieldList(FormField(PaymentForm), validators=[validators.DataRequired()])
    tax_system = IntegerField(default=None)
    email = EmailField(default=None)
    phone_number = StringField(default=None)
    correction_reason = StringField(default=None)
    correction_date = DateField(default=None)
    doc_number = StringField(default=None)
    precept = BooleanField(default=False)





