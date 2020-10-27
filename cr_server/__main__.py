from aiohttp import web
import logging
from apps.service_group import create_app as create_service_group_app
from apps.admin import create_app as create_admin_app
from core.loaders import DefaultModuleLoader
from .settings import CONFIGURATION, HOST


logging.basicConfig(filename="log.log", level=logging.DEBUG)


if __name__ == '__main__':
    container = DefaultModuleLoader().load('configurations', CONFIGURATION)  # Dependency injection container
    app = web.Application(loop=container.loop())
    admin_app = create_admin_app(container.device_group_manager(),  container.service_group_facade(),
                                 container.users_management_service(),
                                 container.access_administration_service(),
                                 container.authentication_service(),
                                 container.authorization_policy(),  container.identity_policy(),
                                 container.device_creation_service(),
                                 session_storage= container.session_storage())
    admin_app.cleanup_ctx.append(container.admin_app_context)
    app.add_subapp('/admin/', admin_app)
    service_group_app = create_service_group_app(container.authentication_service(),
                                                 container.authorization_policy(),
                                                 container.receipt_read_repository(),
                                                 container.receipt_processing_service(),
                                                 container.service_group_facade(),
                                                 container.registrator_info_storage(),
                                                 container.device_group_manager(),
                                                 container.event_dispatcher())
    app.add_subapp('/service_groups/', service_group_app)
    web.run_app(app, **HOST)
