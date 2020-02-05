from abc import ABC, abstractmethod
from contextlib import contextmanager
import time
import asyncio


# Состояния смены
# Чтобы уменьшить код взаимодействия объекта кассы, объекта смены и её состояний и сделать его понятнее
# используем контекстные менеджеры

class ShiftState:
    def __init__(self, shift):
        self.shift = shift

    @contextmanager
    def open(self):
        yield False

    @contextmanager
    def close(self):
        yield False

    def closing_task_cancellation_allowed(self):
        return False

    @property
    def name(self):
        return self.__class__.__name__.lower()

    @property
    def closed(self):
        return False


class Closed(ShiftState):
    @contextmanager
    def open(self):
        yield True
        self.shift.change_state(Opened(self.shift))

    @property
    def closed(self):
        return True


class Opened(ShiftState):
    @contextmanager
    def close(self):
        yield True
        self.shift.change_state(Closed(self.shift))

    def closing_task_cancellation_allowed(self):
        return True


class Closing(ShiftState):
    @contextmanager
    def close(self):
        yield True
        self.shift.change_state(Closed(self.shift))


# Смены

class Shift(ABC):
    # Абстрактный класс кассовой смены. Потомки реализующие методы данного класса реализуют различную логику
    # управления сменой (её длительностью)
    def __init__(self, shift_duration=86400, closing_delay=5, loop=None):

        # Параметры кассовой смены:
        # shift_duration длительность смены (в секундах)
        # shift_closing_delay - на сколько раньше установленного времени начать процедуру окончания смены,
        # данный параметр необходим, чтобы гарантированно закрыть смену во время (если опоздать с закрытием смены,
        # касса перестанет регистрировать фискальные документы), значение по умолчинию - 5 с
        # data_holder_cls - класс, экзкмпляр которого будет хранить данные об оборудовании, его серийные и рег. номера,
        # данные о предприятии, офд
        self.loop = loop if loop else asyncio.get_event_loop()
        self.cash_register = None
        self.duration = shift_duration
        self.closing_delay = closing_delay  # операции с кассой могут быть длительные (особенно, когда связанны c
        # печатью), поэтому необходимо начинать процедуру закрытия смены заблаговременно за shift_closing_delay секунд.
        self._start_time = None
        self._closing_task = None
        self._active = False
        self._state = None

    @property
    def state(self):
        if not self._state:
            self._state = self._start_state
        return self._state

    @property
    @abstractmethod
    def _start_state(self) -> ShiftState:
        pass

    @abstractmethod
    async def activate(self, cash_register):
        pass

    @abstractmethod
    def open(self):
        pass

    async def close(self):
        await self.cash_register.close_shift(self.closing_delay)

    @property
    def active(self):
        # объект смены активен, готов к работе
        return self._active

    @property
    def time_left(self):
        # Возвращается количество секунд оставшееся до закрытия смены
        if self._start_time:
            return self.duration - (time.monotonic() - self._start_time)
        else:
            return None


class ManualShift(Shift):
    # Ручное управление сменой
    @property
    def _start_state(self):
        return Closed(self)

    async def activate(self, cash_register):
        self._active = True

    def open(self):
        self._start_time = time.monotonic()


class AutoShift(Shift):
    # Автоматическая смена, которая закрывается в течении суток (или установленного времени) с момента открытия.
    @property
    def _start_state(self):
        return Closed(self)

    async def activate(self, cash_register):
        if self._active:
            return
        self.cash_register = cash_register
        # активация автоматической смены
        # получаем данные о смене из кассового аппарата:
        cr_state = await self.cash_register.get_shift_state()
        if cr_state['value'] == 1:
            # Если смена открыта, вычисляем время её начала
            self._start_time = time.monotonic() - (cr_state['now_dateTime'].timestamp() -
                                                   cr_state['start_dateTime'].timestamp())
            seconds_to_close = 0 if self.time_left < self.closing_delay else self.time_left - self.closing_delay
            self.open(seconds_to_close, self._start_time)

        elif cr_state['value'] == 2:
            # Если смена просрочена, то время открытия очень давнее (специфика именно того кассового аппарата, под
            # который всё первоначально делалось в том, что если смена просрочена, время старта смены в самом аппарате
            # достоверно не отображается)
            self._start_time = 1
        else:
            self._start_time = None
        # операции с кассой могут быть длительные (особенно, когда связанны с печатью),
        # поэтому необходимо начинать процедуру закрытия смены заблаговременно за shift_closing_delay секунд.
        self._active = True
        if self.time_left is not None and self.time_left <= self.closing_delay:
            self._closing_task = self.closing_timer(0)
            await self.closing_task

    def open(self, seconds_to_close=None, start_time=None):
        # Старт отсчета времени до закрытия смены
        with self.state.open() as openning_allowed:
            if not openning_allowed:
                return
            seconds_to_close = seconds_to_close if seconds_to_close is not None else self.duration - self.closing_delay
            self._start_time = start_time if start_time else time.monotonic()  # Время открытия смены
            # запланировать закрытие смены
            self._closing_task = self.loop.create_task(self.closing_timer(seconds_to_close))

    @contextmanager
    def close(self):
        # Закрытие сменты
        with self.state.close() as closing_allowed:
            if closing_allowed:
                self.cancel_closing_task()
                self._start_time = None
            yield closing_allowed

    async def closing_timer(self, delay):
        await asyncio.sleep(delay)
        # Меняем состояние смены в "завершающееся"
        self.change_state(Closing(self))
        await self.cash_register.close_shift(self.closing_delay)
        self._start_time = None

    @property
    def closing_task(self):
        return self._closing_task

    def cancel_closing_task(self):  # отмена задачи закрытия смены
        if self.state.closing_task_cancellation_allowed():
            self.closing_task.cancel()
            self._closing_task = None
            return True

    def change_state(self, state: ShiftState):
        self._state = state
