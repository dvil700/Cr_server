from dependency_injector import containers, providers
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from hardware.services import AvailableDriversInformationService
from core.csrf import csrf_middleware
from .middlewares import auth_middleware
from .utils import AccessAttributesCalculationStrategy


class AppContainer(containers.DeclarativeContainer):
    driver_information_service = providers.Singleton(AvailableDriversInformationService)
    middlewares = providers.List(csrf_middleware, auth_middleware)
    session_storage = providers.Singleton(EncryptedCookieStorage)
    access_attr_calc_strategy = providers.Singleton(AccessAttributesCalculationStrategy)