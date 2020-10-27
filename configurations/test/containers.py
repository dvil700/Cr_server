from asyncio import get_event_loop
from aiohttp_security.session_identity import SessionIdentityPolicy
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from dependency_injector import containers, providers
from access_control.auth import UserManagementService, UserInMemoryRepository, AuthService, EncryptionService
from access_control.services import AccessAdministrationService
from access_control.authorization_policies import AbacAuthorizationPolicy
from access_control.abac.pbp import AsyncPDB
from access_control.abac.storages.in_memory.storages import InMemoryStorage
from hardware.fiscal_device_group_managers import DeviceGroupManager
from hardware import DefaultFiscalDeviceCreationService
from apps.service_group.facades import FiscalServiceGroupFacade
from apps.service_group.storages.in_memory import ServiceGroupInMemoryStorage
from receipt.receipt_read import InMemoryReceiptRepository
from receipt.services import ReceiptProcessingService
from receipt.registrator_info_storages import InMemoryRegistratorInfoStorage
from core.events import EventDispatcher
from core.events.event_storages import InMemoryEventStorage
from .config import *


async def admin_app_context(app):
    sg = [('first', True, {'driver': {'driver_name': 'atol', 'settings': {'shift_duration': 80000,
                                                                          'cr_model': 'Атол30Ф'}}}),
          ('second', True, {'driver': {'driver_name': 'test', 'settings': {'shift_duration': 80000}}}),
          ('third', True, {'driver': {'driver_name': 'test', 'settings': {'shift_duration': 80000}}})]
    for item in sg:
        await app['fiscal_service_group_facade'].register_new_service_group(*item)
    admin_user = await app['user_management_service'].create_new_user(**ADMIN_USER)
    await app['access_administration_service'].set_access_policy(str(admin_user.id), app['id'], True, True, True)
    yield


class MainContainer(containers.DeclarativeContainer):
    loop = providers.Singleton(get_event_loop)
    service_group_storage = providers.Singleton(ServiceGroupInMemoryStorage)
    service_group_facade = providers.Singleton(FiscalServiceGroupFacade, service_group_storage)

    user_repository = providers.Singleton(UserInMemoryRepository)
    abac_storage = providers.Singleton(InMemoryStorage)
    encryption_service = providers.Singleton(EncryptionService, AUTH_ENCRYPTION_SALT)
    users_management_service = providers.Singleton(UserManagementService, user_repository, encryption_service)
    authentication_service = providers.Singleton(AuthService, user_repository, encryption_service)
    pdp = providers.Singleton(AsyncPDB, abac_storage)
    authorization_policy = providers.Singleton(AbacAuthorizationPolicy, pdp, authentication_service)

    access_administration_service = providers.Singleton(AccessAdministrationService, abac_storage)

    identity_policy = providers.Singleton(SessionIdentityPolicy)

    session_storage = providers.Singleton(EncryptedCookieStorage, SESSION_SECRET,  cookie_name="SSID")

    receipt_read_repository = providers.Singleton(InMemoryReceiptRepository)
    device_group_manager = providers.Singleton(DeviceGroupManager, 'f_devices', loop)
    event_storage = providers.Singleton(InMemoryEventStorage)
    event_dispatcher = providers.Singleton(EventDispatcher, event_storage)
    receipt_processing_service = providers.Singleton(ReceiptProcessingService, device_group_manager, event_dispatcher)

    registrator_info_storage = providers.Singleton(InMemoryRegistratorInfoStorage)
    device_creation_service = providers.Singleton(DefaultFiscalDeviceCreationService, loop, registrator_info_storage)

    admin_app_context=admin_app_context