from abc import ABC, abstractmethod
import importlib.util
import os


class AbstractModuleLoader(ABC):
    # Абстрактный класс загрузчика (фабрики) объекта. Каждый объект, который необходимо загружать динамически, должен
    # иметь свой загрузчик.
    @abstractmethod
    def load(self, **kwargs) -> object:
        pass


class AbstractModuleFromPackageLoader(ABC):
    # Абстрактный класс динамического загрузчика. В параметрах имя пакета, имя модуля и параметры
    @abstractmethod
    def load(self, package_name, module_name, **kwargs) -> object:
        pass


class DefaultModuleLoader(AbstractModuleFromPackageLoader):
    def load(self, package: str, module_name, **kwargs):
        path = os.getcwd()
        # Ищем загрузчик, который инстанциирует объект
        spec = importlib.util.spec_from_file_location('{}.{}.loader'.format(package, module_name),
                                                      '{}/{}/{}/loader.py'.format(path, package.replace('.', '/'),
                                                                                  module_name))
        if spec is None:
            raise ImportError('There is no module with the name {}'.format(module_name))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.Loader().load(**kwargs)
