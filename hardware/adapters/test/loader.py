from core.loaders import AbstractModuleLoader
from .adapter import TestRegistrator


class Loader(AbstractModuleLoader):
    def load(self):
        return TestRegistrator()