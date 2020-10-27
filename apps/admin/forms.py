from wtforms import (Form, StringField, validators, BooleanField, FormField, SelectField, IntegerField, PasswordField)
from wtforms.fields.html5 import EmailField
from wtforms.widgets import HiddenInput
import wtforms_json
wtforms_json.init()

required = validators.DataRequired()


class DriverForm(Form):
    driver_name = SelectField(label=u'')


class SettingsForm(Form):
    driver = FormField(DriverForm, label=u'', render_kw={'class': 'settings-driver-name'})


class ServiceGroupForm(Form):
    id = IntegerField(widget=HiddenInput(), default=0)
    name = StringField(u'Имя группы сервисов', validators=[required, ])
    is_enabled = BooleanField(u'Сервис доступен', default=False)
    settings = FormField(SettingsForm, label=u'Драйвер')


class UserForm(Form):
    login = StringField(u'Логин', validators=[required, ])
    email = EmailField(u'Email')
    is_active = BooleanField(u'Пользователь активен', default=False)
    info = StringField(label=u'Дополнительная информация')
    password = PasswordField(label=u'Пароль')
    password_repeat = PasswordField(label=u'Пароль eще раз')


class AdminPermissionsForm(Form):
    get = BooleanField(label=u'Чтение', default=False)
    post = BooleanField(label=u'Запись', default=False)
    delete = BooleanField(label=u'Удаление', default=False)


class LoginForm(Form):
    login = StringField(validators=[required, ])
    password = StringField(validators=[required, ])
