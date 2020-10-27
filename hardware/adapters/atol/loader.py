import os
import sys
import json
from logging import getLogger
from core.loaders import AbstractModuleLoader
from hardware.adapters.base import DefaultTimeCounter
from .adapter import AtlCashRegister
from .libfptr10 import IFptr
from ..exceptions import DriverLoadError

logger = getLogger(__name__)

_OS_DRIVERS_CONF = 'os_drivers.conf'  # Drivers config file name


class Loader(AbstractModuleLoader):
    @staticmethod
    def get_path(path):
        return '{}/{}'.format(os.path.dirname(__file__), path)

    def get_driver(self, cr_model, cr_port, cr_ofd_channel, cr_baudrate, cr_passwd):
        os_platform = sys.platform.lower()
        int_size = 64 if sys.maxsize > 2 ** 32 else 32
        with open(self.get_path(_OS_DRIVERS_CONF), 'r') as config_file:
            for conf in config_file:
                conf = json.loads(conf)
                conf['int_size'] = conf['int_size'] if conf.get('int_size', None) else int_size
                if not (os_platform == conf['os'] and int_size == conf['int_size']):
                    continue
                else:
                    break
                raise DriverLoadError('There are no drivers matching your operation system')

        path = self.get_path(conf['lib_path'])
        driver = IFptr(path)
        driver.setSingleSetting('UserPassword', str(cr_passwd))
        driver.setSingleSetting(driver.LIBFPTR_SETTING_MODEL, str(cr_model))
        driver.setSingleSetting(driver.LIBFPTR_SETTING_PORT, str(cr_port))
        driver.setSingleSetting(driver.LIBFPTR_SETTING_OFD_CHANNEL, str(cr_ofd_channel))
        driver.setSingleSetting('BaudRate', str(cr_baudrate))
        driver.applySingleSettings()
        driver.open()
        return driver

    def load(self, cr_model, cr_port, cr_ofd_channel, cr_baudrate, cr_passwd, test_mode=False):
        driver = self.get_driver(cr_model, cr_port, cr_ofd_channel, cr_baudrate, cr_passwd)
        counter = DefaultTimeCounter()
        return AtlCashRegister(driver, counter, test_mode=test_mode)
