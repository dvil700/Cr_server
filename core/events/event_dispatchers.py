from abc import ABC, abstractmethod
from core.events.event_storages import AbstractEventStorage
from core.events.events import AbstractEventHandler
from logging import getLogger

logger = getLogger(__name__)


class AbstractEventDispatcher(ABC):
    @abstractmethod
    def add_subscriber(self, command_type: type, subscriber):
        pass

    @abstractmethod
    def detach_subscriber(self, command_type, subscriber):
        pass

    @abstractmethod
    async def handle(self, command):
        pass


class EventDispatcher(AbstractEventDispatcher):
    def __init__(self, event_storage: AbstractEventStorage):
        self._event_subscribers = dict()
        self._event_storage = event_storage

    def add_subscriber(self, event_type: type, subscriber: AbstractEventHandler):
        try:
            self._event_subscribers[event_type].add(subscriber)
        except KeyError as e:
            self._event_subscribers[event_type] = {subscriber}
        finally:
            logger.debug('The event handler %s subscribed on %s', str(subscriber), str(event_type))

    def detach_subscriber(self, event_type, subscriber):
        subscribers = self._event_subscribers.get(event_type, None)
        if not subscribers:
            return
        if subscriber not in subscribers:
            return
        return subscribers[subscriber]

    async def handle(self, event):
        logger.debug('%s handled by %s', str(event), str(self))

        await self._event_storage.add(event)
        if type(event) not in self._event_subscribers:
            return
        for subscriber in self._event_subscribers[type(event)]:
            try:
                await subscriber.handle(event)
            except Exception as e:
                logger.error('Error during handling the event %s, by the handler %s: %s', str(event), str(subscriber),
                             str(e))
