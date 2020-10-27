from typing import Union
import pathlib
from aiohttp import web
from aiohttp_security import AbstractAuthorizationPolicy, AbstractIdentityPolicy, setup as security_setup
from aiohttp_session import setup as session_setup
from aiohttp_session import AbstractStorage, session_middleware
import aiohttp_jinja2
import jinja2
from hardware import (AbstractAvailableDriversInformationService, AbstractDeviceGroupManager, AbstractDeviceCreationService)
from access_control.auth import AbstractUserManagmentService, AbstractAuthenticationService
from access_control.services import AccessAdministrationService
from apps.service_group.facades import AbstractFiscalServiceGroupFacade
from .di_containers import AppContainer
from .urls import get_routes


def create_app(device_group_manager: AbstractDeviceGroupManager,
               fiscal_service_group_facade: AbstractFiscalServiceGroupFacade,
               user_management_service: AbstractUserManagmentService,
               access_administration_service: AccessAdministrationService,
               authentication_service: AbstractAuthenticationService,
               authorization_policy: AbstractAuthorizationPolicy,
               identity_policy: AbstractIdentityPolicy,
               device_creation_service: AbstractDeviceCreationService,
               drivers_information_service: Union[AbstractAvailableDriversInformationService, None] = None,
               session_storage: Union[AbstractStorage, None] = None,
               middlewares: Union[list, None] = None):

    app = web.Application()
    template_loader = jinja2.FileSystemLoader('{}/templates/'.format(pathlib.Path(__file__).parent))
    aiohttp_jinja2.setup(app, context_processors=[aiohttp_jinja2.request_processor, ], loader=template_loader)

    if not session_storage:
        session_storage = AppContainer.session_storage()

    if not middlewares:
        middlewares = AppContainer.middlewares()
        middlewares.insert(0, session_middleware(session_storage))

    app.middlewares.extend(middlewares)

    app['id'] = 'admin'
    app['drivers_information_service'] = drivers_information_service
    if not drivers_information_service:
        app['drivers_information_service'] = AppContainer.driver_information_service()

    app['device_group_manager'] = device_group_manager
    app['device_creation_service'] = device_creation_service
    app['fiscal_service_group_facade'] = fiscal_service_group_facade
    app['user_management_service'] = user_management_service
    app['access_administration_service'] = access_administration_service
    app['authentication_service'] = authentication_service
    app['admin_access_attr_calc_strategy'] = AppContainer.access_attr_calc_strategy()

    app.add_routes(get_routes())
    app.router.add_static('/static/', '{}/static/'.format(pathlib.Path(__file__).parent), show_index=True,
                          append_version=True, name='static')

    session_setup(app, session_storage)
    security_setup(app, identity_policy, authorization_policy)
    return app
