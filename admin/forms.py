from wtforms import StringField, PasswordField, HiddenField, BooleanField, SelectField
from wtforms.validators import InputRequired, StopValidation, EqualTo
from wtforms.widgets import HTMLString, Input as BaseInput, TextInput
from forms import Form
from auth.auth import auth, get_standart_password_check_strategy

m = "Заполните обязательное поле"
required = InputRequired(m)

_input_class = 'form-control'


class InputWidget(BaseInput):
    input_type = 'text'

    def __call__(self, field, **kwargs):
        if len(field.errors) > 0:
            kwargs['class'] = '%s %s' % (kwargs['class'], 'is-invalid')
        return super().__call__(field, **kwargs)


class PasswordWidget(InputWidget):
    input_type = 'password'


class LoginForm(Form):
    login = StringField(u'Имя пользователя', validators=[required, ],
                        render_kw={'class': _input_class, 'placeholder': 'Имя пользователя'})
    passwd = PasswordField(u'Пароль', [required, ], render_kw={'class': _input_class, 'placeholder': 'Пароль'})

    def set_auth_error(self):
        self.passwd.errors.append('Неверный логин либо пароль')


class LoginFormRedirectable(LoginForm):
    redirect = HiddenField()


class PermissionAddingForm(Form):
    name = StringField(u'Название', [required, ], render_kw={'class': _input_class})


class UserForm(Form):
    login = StringField(u'Имя', [required, ], render_kw={'class': _input_class})
    enabled = SelectField(u'Статус', coerce=bool, choices=[(True, 'Включен',), (False, 'Выключен',)])


def _equal_pass(field_name):
    return EqualTo(field_name, message='Пароли должны совпадать')


class PasswdForm(Form):
    passwd = PasswordField(u'Пароль', [required, _equal_pass('confirm')], widget=PasswordWidget(),
                           render_kw={'class': _input_class})
    confirm = PasswordField(u'Подтверждение', [required, _equal_pass('passwd')], widget=PasswordWidget(),
                            render_kw={'class': _input_class})

    @property
    def data(self):
        data=super().data
        data.pop('confirm', None)
        data['passwd'] = get_standart_password_check_strategy().password_encode(data['passwd'])
        return data

class NewUserForm(PasswdForm, UserForm):
    pass


class GroupForm(Form):
    name = StringField(u'Название', [required, ], render_kw={'class': _input_class})
