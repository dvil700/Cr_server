from abc import ABC, abstractmethod
import asyncio
from concurrent.futures import ThreadPoolExecutor
import datetime
import time
from logging import getLogger
from receipt import AbstractReceiptRegistrator, Receipt


logger = getLogger(__name__)


class ReceiptRegistrationError(Exception):
    pass


class AbstractTimeCounter(ABC):
    def get_time_value(self) -> int:
        pass


class DefaultTimeCounter(AbstractTimeCounter):
    def get_time_value(self):
        return time.perf_counter()


# Информация о смене
class ShiftInformation:
    def __init__(self, is_opened: bool, device_request_date_time: datetime.datetime, time_counter: AbstractTimeCounter,
                 counter_request_time: float, number=None, datetime_open=None, datetime_closed=None):
        self._number = number
        self._is_opened = is_opened
        self._datetime_open = datetime_open  # время открытия смены (время в устойстве)
        self._datetime_closed = datetime_closed  # время закрытия смены (время в устройстве)
        self._device_request_date_time = device_request_date_time  # время кассового устройства на момент запроса данных
        self._time_counter = time_counter  # счетчика времени
        self._counter_request_time = counter_request_time  # Время по счетчику, когда был получены данные из кассы

    @property
    def number(self):
        return self._number

    @property
    def is_opened(self):
        return self._is_opened

    @property
    def datetime_open(self):
        return self._datetime_open

    @property
    def datetime_closed(self):
        return self._datetime_closed

    @property
    def time_passed(self) -> (int, None):
        if not self.is_opened:
            return None
        # Сколько секунд прошло с момента открытия смены
        return int(self._device_request_date_time.timestamp() - self.datetime_open.timestamp() +
                   self._time_counter.get_time_value() - self._counter_request_time)


# Абстрактный класс менеджера кассового устройства
class AbstractFiscalDeviceManager(ABC):
    @abstractmethod
    def close_shift(self):
        pass

    @abstractmethod
    def open_shift(self):
        pass

    @abstractmethod
    def set_date_time(self, date_time: datetime.datetime):
        pass

    @abstractmethod
    def get_date_time(self)-> datetime.datetime:
        pass

    @abstractmethod
    def get_shift_info(self) -> ShiftInformation:
        pass

    @abstractmethod
    def reboot(self):
        pass

    @abstractmethod
    def close(self):
        pass


#  Управление устройством и регистрация чеков
class AbstractRegistratorDriverAdapter(AbstractReceiptRegistrator, AbstractFiscalDeviceManager, ABC):
    pass


# Состояние смены
class ShiftState(ABC):
    @abstractmethod
    async def open_shift(self):
        pass

    @abstractmethod
    async def close_shift(self):
        pass

    @abstractmethod
    async def register_receipt(self, receipt: Receipt):
        pass

    @abstractmethod
    def state_changed(self):
        pass


class ShiftStateFactory(ABC):
    @abstractmethod
    def create_state(self, registrator_adapter: AbstractRegistratorDriverAdapter, shift_info: ShiftInformation) -> ShiftState:
        pass

    @abstractmethod
    def create_default_state(self, registrator_adapter: AbstractRegistratorDriverAdapter) -> ShiftState:
        pass


# Интерфейс объекта, управляеммого состоянием смены
class ShiftStateDrivenAbstract(ABC):
    _state: ShiftState
    _loop: asyncio.AbstractEventLoop

    @property
    def loop(self):
        return self._loop

    @property
    def state(self):
        return self._state

    async def do_close_shift(self):
        pass

    async def do_open_shift(self):
        pass

    async def do_register_receipt(self, receipt):
        pass

    async def change_state(self, state: ShiftState):
        pass


# Executor для выполнения синхронного кода асинхронно
class AbstractAsyncExecutor(ABC):
    async def execute(self, func, *args) -> object:
        pass


# Executor для выполнения синхронного кода в треде. Данный класс намеренно использует один worker, что необходимо
# для определенных типов кассового оборудования, чтобы не возникало корфликтов и операции взаимодействия были
# изолированы друг от друга.
class AsyncTreadPoolExecutor(AbstractAsyncExecutor):
    def __init__(self, loop, thread_name_prefix='',
                 initializer=None, initargs=()):
        self._executor = ThreadPoolExecutor(1, thread_name_prefix, initializer, initargs)
        self._loop = loop

    async def execute(self, func, *args):
        return await self._loop.run_in_executor(self._executor, func, *args)


# Асинхронный декоратор для адаптера кассового устройства, с состоянием смены
class AsyncRegistrator(AbstractRegistratorDriverAdapter, ShiftStateDrivenAbstract):
    def __init__(self, adapter: AbstractRegistratorDriverAdapter, state_factory: ShiftStateFactory,
                 loop: asyncio.AbstractEventLoop, executor: AbstractAsyncExecutor):
        self._loop = loop
        self._executor = executor
        self._adapter = adapter
        self._state_factory = state_factory
        self._state = state_factory.create_default_state(self)
        loop.create_task(self.change_state())
        self._shift_info = None
        self._registrator_info = None
        self._id = None

    @property
    def id(self):
        return self._adapter.id

    @id.setter
    def id(self, device_id: int):
        self._adapter.id = device_id

    async def open_shift(self):
        await self._state.open_shift()

    async def close_shift(self):
        await self._state.close_shift()

    async def get_shift_info(self) -> ShiftInformation:
        if self._shift_info:
            return self._shift_info
        self._shift_info = await self._executor.execute(self._adapter.get_shift_info())
        return self._shift_info

    async def register_receipt(self, receipt):
        logger.debug('register_receipt method was called, receipt id = %d. The current state is %s', receipt.id,
                     str(self._state))
        await self._state.register_receipt(receipt)

    async def get_registrator_info(self):
        if self._registrator_info is None:
            self._registrator_info = await self._executor.execute(self._adapter.get_registrator_info)
        return self._registrator_info

    async def set_date_time(self, date_time: datetime.datetime):
        await self._executor.execute(self._adapter.set_date_time, date_time)

    async def get_date_time(self):
        return await self._executor.execute(self._adapter.get_date_time)

    async def reboot(self):
        return await self._executor.execute(self._adapter.reboot)

    async def close(self):
        return await self._executor.execute(self._adapter.close)

    async def do_close_shift(self):
        await self._executor.execute(self._adapter.close_shift)

    async def do_register_receipt(self, receipt):
        await self._executor.execute(self._adapter.register_receipt, receipt)

    async def do_open_shift(self):
        await self._executor.execute(self._adapter.open_shift)

    async def change_state(self, state: ShiftState = None):
        old_state = self._state
        logger.info('The receipt registrator state started to change. The old state: %s', str(self._state))
        if state:
            self._state = state
        else:
            # Если состояние смены не передано в аргументе метода, то вычесляем его в фабрике состояний
            self._shift_info = await self._executor.execute(self._adapter.get_shift_info)
            self._state = self._state_factory.create_state(self, self._shift_info)
        old_state.state_changed()


# Состояние смены - "смена открыта", с таймером на автоматическое закрытие смены
class AutoShiftOpenState(ShiftState):
    def __init__(self, driver_adapter: ShiftStateDrivenAbstract, shift_time_left_seconds: int):
        self._driver_adapter = driver_adapter
        self._state_changed_future = driver_adapter.loop.create_future()
        self._closing_task = driver_adapter.loop.create_task(self._close_shift_later(shift_time_left_seconds))
        self._closing_task_executing = False  # Находится в True когда происходит непосредственно закрытие смены по
        # таймеру (когда счетчик уже отработал - на финишной стадии). Нужно, чтобы _closing_task при закрытии смены
        # не отменял сам себя, и не происходило конфликтов с другими одновременными асинхронными вызовами

    async def _close_shift_later(self, timeout):
        # Таймер закрытия смены
        if timeout != 0:
            self._closing_task_executing = await asyncio.sleep(timeout, True)
        await self.close_shift()

    async def open_shift(self):
        pass

    async def close_shift(self):
        self._cancel_closing_task()
        await self._driver_adapter.do_close_shift()

    async def register_receipt(self, receipt):
        #import pdb; pdb.set_trace()
        if self._closing_task_executing:
            # если запрос на регистрацию чека пришел во время процесса закрытия смены, то дожидаемся закрытия
            # смены, и поручаем выполнение метода следующему состоянию
            await self._closing_task
            await self._state_changed_future
            return await self._driver_adapter.state.register_receipt(receipt)
        return await self._driver_adapter.do_register_receipt(receipt)

    def state_changed(self):
        self._cancel_closing_task()
        self._state_changed_future.set_result(True)
        logger.info('The receipt registrator state was changed. The old state: %s, the new state: %s',
                    str(self), str(self._driver_adapter.state))

    def _cancel_closing_task(self):
        if not self._closing_task_executing:
            self._closing_task.cancel()


# Неопределенное промежуточное состояние смены. Его цель - при вызове методов интерфейса состояния ожидать, пока
# подходящее состояние не установится.
class UndefinedState(ShiftState):
    def __init__(self, driver_adapter: ShiftStateDrivenAbstract):
        self._driver_adapter = driver_adapter
        self._loop = driver_adapter.loop
        self._state_changed_future = self._loop.create_future()

    async def register_receipt(self, receipt: Receipt):
        # Если вызов метода регистрации чека пришел раньше, чем определилось состояние смены, ждем пока
        # определелится и поручаем выполнение следующему состоянию
        await self._state_changed_future
        await self._driver_adapter.state.register_receipt(receipt)

    async def open_shift(self):
        await self._state_changed_future
        await self._driver_adapter.state.open_shift()

    async def close_shift(self):
        await self._state_changed_future
        await self._driver_adapter.state.close_shift()

    def state_changed(self):
        self._state_changed_future.set_result(True)
        logger.info('The receipt registrator state was changed. The old state: %s, the new state: %s',
                    str(self), str(self._driver_adapter.state))


class ClosedState(ShiftState):
    def __init__(self, driver_adapter: ShiftStateDrivenAbstract):
        self._driver_adapter = driver_adapter

    async def register_receipt(self, receipt):
        await self._driver_adapter.do_register_receipt(receipt)
        await self._driver_adapter.change_state()

    async def open_shift(self):
        await self._driver_adapter.state.open_shift()

    async def close_shift(self):
        pass

    async def do_close_shift(self):
        pass

    def state_changed(self):
        logger.info('The receipt registrator state was changed. The old state: %s, the new state: %s',
                    str(self), str(self._driver_adapter.state))


class DefaultStateFactory(ShiftStateFactory):
    def __init__(self, shift_duration: int):
        self._shift_duration = shift_duration  # Длительность сменты

    def create_default_state(self, registrator_adapter: ShiftStateDrivenAbstract) -> ShiftState:
        return UndefinedState(registrator_adapter)

    def create_state(self, registrator_adapter: ShiftStateDrivenAbstract, shift_info: ShiftInformation) -> ShiftState:
        if not shift_info.is_opened:
            return ClosedState(registrator_adapter)
        shift_left_time = self._shift_duration - shift_info.time_passed
        shift_left_time = shift_left_time if shift_left_time>0 else 0
        return AutoShiftOpenState(registrator_adapter, shift_left_time)
