from wtforms import Form as BaseForm, IntegerField

import wtforms_json
wtforms_json.init()


class Form(BaseForm):
    shift_duration = IntegerField('Длительность смены в секундах')
    pass
