from typing import Union
from wtforms import Form
from core.loaders import DefaultModuleLoader


def create_fiscal_device_config_form(driver_name: str, settings: Union[dict, None] = None) -> Form:
    if settings:
        return DefaultModuleLoader().load(__package__, driver_name, **settings)
    return DefaultModuleLoader().load(__package__, driver_name)
