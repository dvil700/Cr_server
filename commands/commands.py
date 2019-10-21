import asyncio
from commands import models
from datetime import datetime
from commands.fields import Group_of_fields, Integer_field
from commands.fields import Decimal_field, EmailOrPhone_field, Group_list, Product, Payment
from commands.states import State, In_proccess, With_warning, Fail
from drivers.atol10_adapter import CROperationError


class Priority:
    def __init__(self, default=0):
        self.default = default

    def __set__(self, obj, value):
        if not isinstance(value, int):
            raise ValueError(text='Value must be integer')
        obj._priority = value

    def __get__(self, obj, object_type):
        value = getattr(self, '_priority', None)
        if value:
            return value
        return self.default


class Command(Group_of_fields):
    # Базовый класс для всех команд
    priority = Priority(0)
    client_operation_id = Integer_field()  # id операции в системе клиента
    client_operation_datetime = Integer_field()  # Unix Time операции в системе клиента в секундах

    def __init__(self, user_id, incoming_dict=None, loop=None):
        self.user_id = user_id
        self.data_dict = incoming_dict
        self.fields = self.get_fields()
        self._error_list = []
        self._name = ''
        self.model_operations = models.Operations()
        if not loop:
            loop = asyncio.get_event_loop()
        self.loop = loop
        self._result = None

    async def get_repeated_operation(self):
        # метод запрашивает у модели данные о выполнении данной команды клиента (нужно для того
        # чтобы избежать повторной обработки команды). Если она уже поступила в обработку возвращается
        # её id (состояние выполнения команды отслеживается по другому адресу)
        if not self.is_valid:
            raise RuntimeError('Метод нельзя применять к невалидным данным')
        user_id = self.user_id
        cop_id = self.data_dict['client_operation_id']
        cop_dt = datetime.fromtimestamp(self.data_dict['client_operation_datetime']).strftime('%Y-%m-%d %H:%M:%S')
        result = await self._search_this_operation_in_db(user_id, cop_id, cop_dt)
        if result:
            return result['id']
        else:
            return None

    async def add_new_in_db(self):
        if not self.is_valid:
            raise RuntimeError('Метод нельзя применять к невалидным данным')
        status = await self.define_state()
        cop_id = self.data_dict['client_operation_id']
        cop_dt = datetime.fromtimestamp(self.data_dict['client_operation_datetime']).strftime('%Y-%m-%d %H:%M:%S')
        self.id = await self.model_operations.add_new_onperation(self.user_id, self.__class__.__name__, cop_id, cop_dt,
                                                                 status.value, self.data_dict)
        return self.id

    async def repeated_request_represent(self):
        # Такие данные возвращаются, когда запрос на выполнение одной команды направлен повторно:
        id = await self.get_repeated_operation()
        return {'status': 208, 'id': id}

    def represent(self):
        return self.state.represent()

    async def define_state(self, status=None):
        # выбор (определение) состояния операции (объекта команды)
        if getattr(self, 'state', None) is None:
            await asyncio.sleep(0)
            self.state = State.define_state(self, 0)
        else:
            self.state = State.define_state(self, status)
            await self.model_operations.update_status(self.id, self.state.value)
        return self.state

    # Отображение данных в зависимости от статуса (состояния):

    def in_proccess_represent(self):
        return {'status': 202, 'id': self.id}

    def success_represent(self):
        result = self._result
        return {'status': 200, 'id': self.id, 'result_data': result}

    def with_warning_represent(self):
        result = self._result
        return {'status': 211, 'id': self.id, 'result_data': result, 'errors': self.get_errors()}

    def fail_represent(self):
        return {'status': 500, 'id': self.id, 'errors': self.get_errors()}

    async def add_result_in_db(self):
        await self.model_operations.add_result(self.id, result=self._result, errors=self.get_errors())

    async def get_result_from_db(self):
        data = await model_operations.get_results(self, self.id, get_errors=True)
        self._result = json.loads(data['result'])
        self._error_list = json.loads(data['errors'])

    async def _search_this_operation_in_db(self, user_id, cop_id, cop_dt):
        result = await self.model_operations.get_proccessed_operation_id(user_id, cop_id, cop_dt)
        return result

    def validate(self):
        result = super().validate(self.data_dict, None, self)
        self._is_valid = True if len(self._error_list) == 0 else False
        return self._is_valid

    @property
    def is_valid(self):
        if getattr(self, '_is_valid', None) is None:
            self.validate()
        return getattr(self, '_is_valid', None)

    def _add_error(self, route, data):
        self._error_list.append({'field': route, 'text': data})

    def get_errors(self):
        return self._error_list if len(self._error_list) > 0 else None

    def __eq__(self, other):
        return self.priority == other.priority

    def __ne__(self, other):
        return self.priority != other.priority

    def __lt__(self, other):
        return self.priority < other.priority

    def __gt__(self, other):
        return self.priority > other.priority

    def __le__(self, other):
        return self.priority <= other.priority

    def __ge__(self, other):
        return self.priority>=other.priority

    def __getitem__(self, key):
        return self.data_dict[key]

    async def wait_executed(self):
        # Метод для ожидания выполнения команды извне (например, чтобы дождаться выполнения и отдать результат в одном соединении)
        if self.state.value > 0:
            await asyncio.sleep(0)
            return
        if not getattr(self, _result_future, None):
            self._result_future = self.loop.create_future()
        if self._result_future.canceled():
            await asyncio.sleep(0)
            return
        await self._result_future

    async def execute(self, executor=None):
        if not self.state.executable:
            return False
        result = await self._execute(executor)
        self._result = result
        if not getattr(self, '_result_future', None):
            self._result_future = self.loop.create_future()
        self._result_future.set_result(True)

        await self.add_result_in_db()  # записываем результаты в db
        return result

    async def _execute(self, executor=None):
        # метод для конкретной реализации выполнения команды, у каждой команды свой
        await asyncio.sleep(0)
        return True


class Fiscal_operation(Command):
    # Фискальные операции (команды)
    async def add_result_in_db(self):
        params_order = ('documentType', 'documentNumber', 'receiptType', 'fiscalSign',
                        'fnSerialNumber', 'documentDate', 'document_summ',)
        args = (self._result[key] for key in params_order)
        await self.model_operations.add_fiscal_document(self.id, *args)

    async def get_result_from_db(self):
        data = await self.model_operations.get_fiscal_operation_results(self, self.id, get_errors=True)
        self._result = json.loads(data['result'])
        self._error_list = json.loads(data['errors'])


class Register_sale(Fiscal_operation):
    # Регистрируем продажу
    email = EmailOrPhone_field()
    total = Decimal_field()
    payments = Group_list(Payment())
    products = Group_list(Product())
    receiptType = Integer_field(allowed_values=tuple(i for i in range(1, 11)))

    def current_validation(self, data_dict, route, command_instance=None):
        if len(self._error_list) == 0:
            payments_total = self.payments.get_totals(data_dict)
            products_total = self.products.get_totals(data_dict)
            if payments_total != data_dict['total']:
                self._add_error(route, 'Сумма платежей и сумма документа не совпадают')
                self._is_valid = False
            if products_total != data_dict['total']:
                self._add_error(route, 'Сумма стоимостей товаров и сумма фискального документа не совпадают')
                self._is_valid = False
        return data_dict

    async def _execute(self, executor):
        cr_driver = executor

        try:
            args = dict(receiptType=1, operator=None, is_electronary=True, r1192=None)
            result = await cr_driver.register_operation(self['email'], self['products'], self['payments'],
                                                        self['total'],
                                                        *args.values())
            await self.state.success()
            return result
        except CROperationError as e:
            self.state.fail()
            self._add_error(e.route, e.data)
            return None


_COMMANDS_ALLOWED = {
    'Register_sale': Register_sale

}


def choose_command(user_id, data_dict):
    if 'command' not in data_dict:
        return False
    command_name = str(data_dict['command']).lower().capitalize()
    if command_name in _COMMANDS_ALLOWED:
        choozen_command = _COMMANDS_ALLOWED[command_name](user_id, incoming_dict=data_dict)
        return choozen_command
    else:
        return False


async def get_already_executed(operation_id, user_id):
    model_operations = model.Operations()
    data = await model_operations.get_operation_by_id(operation_id, user_id)
    current_command = choose_command(user_id, data)
    current_command.define_state(data['status'])
    await current_command.get_results_from_db()
    return current_command
