import pytest
from core.events import Event, EventDispatcher, AbstractEventStorage
from mock import Mock
import datetime


pytestmark = pytest.mark.asyncio


class SomeEntityEvent(Event):
    def __init__(self):
        self._data = {'key': 1}
        self._entity = 'some_entity'
        self._entity_id = 1
        self._date_time = datetime.datetime.now()
        self._user_id = 10
        self._retry = False
        self._client_id = 30


class AsyncStorageWrapper(AbstractEventStorage):
    def __init__(self, storage):
        self._storage = storage

    async def add(self, event):
        self._storage.add(event)

    def get_by_time(self, datetime_start, datetime_finish, event_types: list = None):
        pass

    def get_last_record(self):
        pass


class TestEvents:
    async def test_dispatcher(self):

        event_storage = Mock()
        async_event_storage = AsyncStorageWrapper(event_storage)

        event_dispatcher = EventDispatcher(async_event_storage)
        some_event_handler1 = Mock()
        some_event_handler2 = Mock()
        SomeEntityEvent2 = type('SomeEntityEvent2', (SomeEntityEvent,), {})
        event_dispatcher.add_subscriber(SomeEntityEvent, some_event_handler1)
        event_dispatcher.add_subscriber(SomeEntityEvent2, some_event_handler2)

        event1 = SomeEntityEvent()
        event2 = SomeEntityEvent2()
        await event_dispatcher.handle(event1)
        assert SomeEntityEvent in map(type, event_storage.add.call_args.args)

        await event_dispatcher.handle(event2)
        assert SomeEntityEvent2 in map(type, event_storage.add.call_args.args)

        assert SomeEntityEvent in map(type, some_event_handler1.handle.call_args.args)
        assert SomeEntityEvent not in map(type, some_event_handler2.handle.call_args.args)

        assert SomeEntityEvent2 in map(type, some_event_handler2.handle.call_args.args)
        assert SomeEntityEvent2 not in map(type, some_event_handler1.handle.call_args.args)
