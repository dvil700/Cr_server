from dependency_injector import providers, containers
from access_control.middlewares import BasicAuthMiddleware
from receipt.services import ReceiptCreationService


class AppContainer(containers.DeclarativeContainer):
    receipt_creation_service = providers.Singleton(ReceiptCreationService)
    middlewares = providers.List(BasicAuthMiddleware())
