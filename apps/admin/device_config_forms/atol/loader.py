from core.loaders import AbstractModuleLoader
from .form import Form


class Loader(AbstractModuleLoader):
    def load(self, **kwargs):
        return Form.from_json(kwargs)