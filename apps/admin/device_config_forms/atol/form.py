from wtforms import Form as BaseForm, StringField, BooleanField, IntegerField, SelectField
from wtforms.validators import InputRequired

import wtforms_json
wtforms_json.init()

required = InputRequired('Заполните обязательное поле')

_models = [(57 , 'ATOL 25F'), (61, 'ATOL 30F'), (62, 'ATOL  55F'), (63, 'ATOL  22F'), (64, 'ATOL  52F'),
           (67, 'ATOL  11F'), (69, 'ATOL  77F'), (72, 'ATOL  90F'), (75, 'ATOL  60F'), (77, 'ATOL  42FS'),
           (78, 'ATOL  15F'), (80, 'ATOL  50F'), (81, 'ATOL  20F'), (82, 'ATOL  91F'), (84, 'ATOL  92F'),
           (86, 'ATOL  SIGMA_10'), (87, 'ATOL  27F'), (90, 'ATOL  SIGMA_7F'), (91, 'ATOL  SIGMA_8F'),
           (93, 'ATOL  1F'), (76,'KAZNACHEY FA'),  (500, 'ATOL AUTO')]

_baudrates = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]

_ports = ('COM','USB', 'TCP/IP', 'BLUETOOTH')


class Form(BaseForm):
    shift_duration = IntegerField('Длительность смены в секундах')
    cr_model = SelectField(u'Модель', choices=_models, validators=[required, ], coerce=int)
    cr_port = SelectField(u'Порт', choices=list(enumerate(_ports)), validators=[required, ], coerce=int)
    cr_ofd_channel = SelectField(u'ОФД Канал', choices=((0, 'Неактивирван'), (2, 'Авто')), coerce=int,
                                 validators=[required, ])
    cr_baudrate = SelectField(u'Скорость порта', choices=_baudrates, validators=[required, ], coerce=int)
    cr_passwd = StringField(u'Пароль пользователя', validators=[required, ])
    test_mode = BooleanField(default=False)


