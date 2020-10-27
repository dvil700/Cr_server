import pytest
from hardware.adapters.base import (AsyncTreadPoolExecutor, AsyncRegistrator, AbstractRegistratorDriverAdapter, ShiftInformation,
                                    ShiftStateDrivenAbstract, ShiftStateFactory, ShiftState, UndefinedState, AutoShiftOpenState)
import asyncio
from time import sleep
from mock import Mock, AsyncMock

pytestmark = pytest.mark.asyncio


class TestExecutor:
    def blocking(self, x, y):
        sleep(0.1)
        return x+y

    def one(self):
        sleep(0.3)
        return 1

    def two(self):
        sleep(0.1)
        return 2

    async def test_executor(self):
        loop = asyncio.get_event_loop()
        executor = AsyncTreadPoolExecutor(loop)
        result = await executor.execute(self.blocking, 4, 5)
        assert result == 9

        result = await asyncio.gather(executor.execute(self.one), executor.execute(self.two))
        assert result[0] == 1 and result[1] == 2


class MockState(ShiftState):
    def __init__(self):
        self.open_shift = AsyncMock()
        self.close_shift = AsyncMock()
        self.register_receipt = AsyncMock()
        self.state_changed = Mock()

    def open_shift(self):
        pass

    def close_shift(self):
        pass

    def register_receipt(self, receipt):
        pass

    def state_changed(self):
        pass


class MockStateFactory(ShiftStateFactory):
    def create_default_state(self, registrator_adapter: AbstractRegistratorDriverAdapter) -> ShiftState:
        return MockState()

    def create_state(self, registrator_adapter: AbstractRegistratorDriverAdapter, shift_info: ShiftInformation) -> ShiftState:
        return MockState()


class TestCrRegistrator:
   async def test_registrator(self):
        loop = asyncio.get_event_loop()
        executor = AsyncTreadPoolExecutor(loop)
        sync_device_adapter = Mock() # Адаптер кассового драйвера
        state_factory = MockStateFactory()
        loop = asyncio.get_event_loop()
        registrator = AsyncRegistrator(sync_device_adapter, state_factory, loop, executor)

        await registrator.close_shift()
        assert registrator.state.close_shift.called

        await registrator.open_shift()
        assert registrator.state.open_shift.called

        await registrator.register_receipt(Mock())
        assert registrator.state.register_receipt.called

        await registrator.do_register_receipt(Mock())
        assert sync_device_adapter.register_receipt.called

        await registrator.do_close_shift()
        assert sync_device_adapter.close_shift.called

        await registrator.do_open_shift()
        assert sync_device_adapter.open_shift.called

        old_state = registrator.state
        await registrator.change_state()
        assert old_state!=registrator.state
        assert old_state.state_changed.called


# Тестирование состояний смены
class MockStateFull(ShiftStateDrivenAbstract):
    # Класс объекта, управляемого состоянием
    def __init__(self):
        self.do_close_shift = AsyncMock()
        self.do_register_receipt = AsyncMock()
        self.do_open_shift = AsyncMock()
        self._loop = asyncio.get_event_loop()
        self._state = MockState()

    def change_state(self, state):
        old_state = self._state
        self._state = state if state else MockState()
        old_state.state_changed()


class TestStates:
    async def test_undefined_state(self):
        statefull_registrator = MockStateFull()
        methods = {'close_shift':[], 'open_shift':[], 'register_receipt':[Mock()]}
        for method, args in methods.items():
            state = UndefinedState(statefull_registrator)

            task = asyncio.create_task(getattr(state, method)(*args))
            await asyncio.sleep(0)
            assert task.done() == False

            new_state = MockState()
            statefull_registrator.change_state(new_state)
            state.state_changed()
            await asyncio.sleep(0)
            assert task.done() == True
            assert getattr(new_state, method).called

    async def test_auto_shift_state(self, event_loop):
        statefull_registrator = MockStateFull()
        default_state = MockState()
        statefull_registrator._state = default_state # Установим дефолтную смену

        shift_time_left_seconds = 1 # Через сколько секунд необходимо закрыть смену
        state = AutoShiftOpenState(statefull_registrator, shift_time_left_seconds)
        state.state_changed = Mock()  # Подменим метод для проверки
        statefull_registrator.change_state(state)
        default_state.state_changed()
        assert default_state.state_changed.called

        await state.register_receipt(Mock())
        await state.open_shift()

        # В состоянии AutoShiftOpenState должны регистрироваться документы, но не должно происходить открытие смены
        # (она и так открыта)
        assert statefull_registrator.do_register_receipt.called
        assert not statefull_registrator.do_open_shift.called

        # Спустя заданный промежуток времени смена должна быть закрыта и состояние смены должно измениться тоже
        await asyncio.sleep(shift_time_left_seconds+0.1)
        assert statefull_registrator.do_close_shift.called
        state.state_changed()
        assert state.state_changed.called

        # Протестируем пограничное состояние, когда смена находится в состоянии закрытия по таймеру - атрибут
        # self._closing_task_executing принимет значение True
        statefull_registrator = MockStateFull()
        default_state = MockState()
        statefull_registrator._state = default_state

        shift_time_left_seconds = 1
        state = AutoShiftOpenState(statefull_registrator, shift_time_left_seconds)
        statefull_registrator.change_state(state)
        state._closing_task_executing = True

        event_loop.create_task(state.register_receipt(Mock()))
        await asyncio.sleep(0.5)
        assert not statefull_registrator.do_register_receipt.called
        await state._closing_task # Дождемся, закрытия смены
        assert statefull_registrator.do_close_shift.called # Удостоверяемся, что метод закрытия смены был вызван
        statefull_registrator.change_state(MockState())
        await asyncio.sleep(0)
        assert statefull_registrator.state.register_receipt.called # Вызов метода регистрации чека должен быть вызван
        # уже через новое состояние





