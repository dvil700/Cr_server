from core.loaders import AbstractModuleLoader
from .containers import MainContainer


class Loader(AbstractModuleLoader):
    def load(self, **kwargs):
        return MainContainer