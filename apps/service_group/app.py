from typing import Union
from aiohttp.web import Application
from aiohttp_security import AbstractAuthorizationPolicy, AbstractIdentityPolicy, setup as security_setup
from access_control.auth import AbstractAuthenticationService
from core.events import AbstractEventDispatcher
from receipt.services import AbstractReceiptProcessingService
from receipt.receipt_read import AbstractReceiptRepository
from receipt.registrator_info_storages import AbstractRegistratorDataStorage
from receipt.receipt_read.event_handlers import (ReceiptCreatedHandler, ReceiptReceiptRegisteredHandler,
                                                 ReceiptReceiptRegistationFailedHandler)
from hardware.fiscal_device_group_managers import (AbstractDeviceGroupManager, CommandProcessorInterface,
                                                   DeviceAvailabilityCheck)
from .access_control import AccessAttributesCalculation
from .facades import AbstractFiscalServiceGroupFacade
from .di_containers import AppContainer
from .urls import get_routes


def gen(value):
    while True:
        value = value + 1
        yield value


async def context(app):
    app['receipt_id_generator'] = gen(await app['receipt_read_repository'].get_last_id())
    yield


def create_app(authentication_service: AbstractAuthenticationService,
               authorization_policy: AbstractAuthorizationPolicy,
               receipt_read_repository: AbstractReceiptRepository,
               receipt_processing_service: AbstractReceiptProcessingService,
               service_group_facade: AbstractFiscalServiceGroupFacade,
               registrator_data_storage: AbstractRegistratorDataStorage,
               device_manager: Union[AbstractDeviceGroupManager, CommandProcessorInterface, DeviceAvailabilityCheck],
               event_dispatcher: AbstractEventDispatcher):

    app = Application()
    if getattr(AppContainer, 'middlewares', None):
        app.middlewares.extend(AppContainer.middlewares())
    app['receipt_read_repository'] = receipt_read_repository
    app['authentication_service'] = authentication_service
    app['access_attr_calc_strategy'] = AccessAttributesCalculation()
    app['receipt_creation_service'] = AppContainer.receipt_creation_service()
    app['receipt_processing_service'] = receipt_processing_service
    app['fiscal_service_group_facade'] = service_group_facade
    app['device_manager'] = device_manager
    app['registrator_data_storage'] = registrator_data_storage
    app['event_dispatcher'] = event_dispatcher

    app['event_handlers'] = [ReceiptCreatedHandler(receipt_read_repository),
                             ReceiptReceiptRegisteredHandler(receipt_read_repository, registrator_data_storage),
                             ReceiptReceiptRegistationFailedHandler(receipt_read_repository)]

    app['authorization_policy'] = authorization_policy

    for handler in app['event_handlers']:
        handler.subscribe(event_dispatcher)

    app.cleanup_ctx.append(context)
    app.add_routes(get_routes())

    return app
