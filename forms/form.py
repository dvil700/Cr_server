from wtforms import Form as BaseForm
from wtforms.widgets import ListWidget


class Form(BaseForm):
    def as_ul(self):
        widget = ListWidget()
        return widget(self)
