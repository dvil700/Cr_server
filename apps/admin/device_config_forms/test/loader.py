from core.loaders import AbstractModuleLoader
from .form import Form


class Loader(AbstractModuleLoader):
    def load(self, *args, **kwargs):
        return Form(*args, **kwargs)