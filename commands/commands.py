import asyncio
import json
from commands.models import Operation, FiscalDocument, IncomeData, CommandStates
from datetime import datetime
from commands.fields import GroupOfFields, IntegerField
from commands.fields import DecimalField, EmailorphoneField, GroupList, Product, Payment
from commands.states import state_map
from drivers.atol10_adapter import CROperationError


class Priority:
    # Дескриптор приоритета для команд. При исполнении команд в объекте invoker используется очередь с приоритетами.
    # Чем выше приоритет у команды, тем раньше она выполнится.
    def __init__(self, default=0):
        self.default = default

    def __set__(self, obj, value):
        if not isinstance(value, int):
            raise ValueError('The value must be integer')
        obj._priority = value

    def __get__(self, obj, object_type):
        value = getattr(self, '_priority', None)
        if value:
            return value
        return self.default


class Command(GroupOfFields):
    # Базовый класс для всех команд
    priority = Priority(0)
    client_operation_id = IntegerField()  # id операции в системе клиента
    client_operation_datetime = IntegerField()  # Unix Time операции в системе клиента в секундах

    def __init__(self, user_id, db_object, incoming_dict=None, datetime_add=None, state_map_list=state_map,
                 loop=None):
        self.user_id = user_id
        self.data_dict = incoming_dict
        if not datetime_add and isinstance(incoming_dict, dict):
            datetime_add = incoming_dict.get('datetime_add', None)
        self.datetime_add = datetime_add
        self.fields = self.get_fields()
        self._error_list = []
        self._name = ''
        self.db_object = db_object
        if not loop:
            loop = asyncio.get_event_loop()
        self.loop = loop
        self.state_map = state_map_list
        self._result = None
        self._result_future = None

    async def check_if_repeated(self):
        # метод запрашивает у модели данные о выполнении данной команды клиента (нужно для того
        # чтобы избежать повторной обработки команды). Если она уже поступила в обработку возвращается
        # её id (состояние выполнения команды отслеживается по другому адресу)
        if not self.is_valid:
            raise RuntimeError('Метод нельзя применять к невалидным данным')
        user_id = self.user_id
        cop_id = self.data_dict['client_operation_id']
        cop_dt = datetime.fromtimestamp(self.data_dict['client_operation_datetime']).strftime('%Y-%m-%d %H:%M:%S')
        result = await Operation.get_proccessed_operation_id(user_id, cop_id, cop_dt, self.db_object)
        if result:
            return result['id']
        else:
            return None

    async def add_new_in_db(self):
        # Добавление информации о новой операции в базу данных
        if not self.is_valid:
            raise RuntimeError('Метод нельзя применять к невалидным данным')
        state = await self.define_state()
        cop_id = self.data_dict['client_operation_id']
        cop_dt = datetime.fromtimestamp(self.data_dict['client_operation_datetime'])

        operation = Operation(command=self.__class__.__name__, user_id=self.user_id, client_operation_id=cop_id,
                              client_operation_datetime=cop_dt, datetime_add=self.datetime_add,
                              state=self.state.value_string, datetime_modify=datetime.now())
        async with self.db_object.conn as conn:
            try:
                transaction = await conn.begin()
                self.id = (await conn.execute(operation.add())).lastrowid
                excluded = {'user_id', 'command', 'client_operation_id', 'client_operation_datetime'}
                data = {k: i for k, i in self.data_dict.items() if k not in excluded}
                await conn.execute(IncomeData(operation_id=self.id, data=json.dumps(data)).add())
            except Exception as e:
                await transaction.rollback()
                raise e
            await transaction.commit()
        return self.id

    async def repeated_request_represent(self):
        # Такие данные возвращаются, когда запрос на выполнение одной команды направлен повторно:
        command_id = self.data_dict['client_operation_id']
        if command_id:
            return {'status': 208, 'id': command_id}
        else:
            return None

    def represent(self):
        return self.state.represent()

    async def define_state(self, state=None):
        # выбор (определение) состояния операции (объекта команды)
        if getattr(self, 'state', None) is None:
            self.state = self.state_map[0](self)
        elif state is not None:
            self.state = self.state_map[state](self)
            await self.db_object.query(Operation.update.where(Operation.id == self.id).
                                       values(state=self.state.value_string))
        return self.state

    # Отображение данных в зависимости от состояния:

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
        # Добавление результата команды в базу данных
        result = json.dumps(self._result) if self._result else None
        errors = json.dumps(self.get_errors()) if self.get_errors() else None
        await self.db_object.query(Operation.update().where(Operation.user_id == self.id). \
                                   values(result=result, errors=errors))

    async def get_result_from_db(self):
        # Достать результат из базы данных
        data = await self.db_object.query(Operation.query.filter(Operation.id == self.id). \
                                          with_entities(Operation.result, Operation.errors).statement)
        self._result = json.loads(data['result'])
        self._error_list = json.loads(data['errors'])

    def validate(self, data=None, route=None, main_parent=None):
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

    def cmp_with_date(self, other):
        if self.priority == other.priority:
            # При равном приоритете команд, "главнее" та, которая раньше пришла
            return self.datetime_add < other.datetime_add
        else:
            return False

    def __lt__(self, other):
        if self.priority < other.priority:
            return True
        return self.cmp_with_date(other)

    def __gt__(self, other):
        if self.priority > other.priority:
            return True
        return self.cmp_with_date(other)

    def __le__(self, other):
        if self.priority <= other.priority:
            return True
        return self.cmp_with_date(other)

    def __ge__(self, other):
        if self.priority >= other.priority:
            return True
        return self.cmp_with_date(other)

    def __getitem__(self, key):
        return self.data_dict[key]

    async def wait_executed(self):
        # Метод для ожидания выполнения команды извне (например, чтобы дождаться выполнения и отдать результат в
        # одном соединении)
        if self.state.value > 0:
            await asyncio.sleep(0)
            return
        if not getattr(self, '_result_future', None):
            self._result_future = self.loop.create_future()
        if self._result_future.cancelled():
            await asyncio.sleep(0)
            return
        await self._result_future

    async def execute(self, executor=None):
        # Исполнение команды, executor - объект для взаимодействия с кассой (или другой частью системы)
        if not self.state.executable:
            return False
        self._result =  await self._execute(executor)
        # _result_future - asyncio future, в данном контектсе служит для создания возможности отдачи результата
        # выполнения команды клиенту за одно подключение (в пределах установленного таймаута конечно)
        if not getattr(self, '_result_future', None):
            self._result_future = self.loop.create_future()
        if not self._result_future.done() or not self._result_future.cancelled():
            self._result_future.set_result(True)
        await self.add_result_in_db()  # записываем результаты в db
        return self._result

    async def _execute(self, executor):
        # метод для конкретной реализации выполнения команды, у каждой команды свой
        await asyncio.sleep(0)
        return True


class FiscalOperation(Command):
    # Фискальные операции (команды)
    async def add_result_in_db(self):
        cr_data = self._result.pop('cr_data')
        fd = FiscalDocument(operation_id=self.id, online_cr_id=cr_data['online_cr_id'], **self._result)
        self._result['cr_data'] = cr_data
        await self.db_object.query(fd.add())

    async def get_result_from_db(self):
        fd = FiscalDocument
        sql = fd.query.oterjoin(Operation.id).with_entities(fd.documentNumber, fd.receiptType,
                                                            fd.fiscalSign, fd.fnSerialNumber, fd.documentDate,
                                                            fd.document_summ, Operation.errors).statement.apply_labels()
        data = await self.db_object.query(sql)
        self._error_list = json.loads(data['errors'])
        self._result = data


class Register_sale(FiscalOperation):
    # Регистрируем продажу
    email = EmailorphoneField()
    total = DecimalField()
    payments = GroupList(Payment())
    products = GroupList(Product())
    receiptType = IntegerField(allowed_values=tuple(i for i in range(1, 11)))

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
                                                        self['total'], *args.values())
            await self.state.success()
            return result
        except CROperationError as e:
            self.state.fail()
            self._add_error(e.route, e.data)
            return None


COMMANDS_ALLOWED = {'Register_sale': Register_sale}


def choose_command(command_name, user_id, db_object, data_dict, datetime_add=None):
    if 'command' not in data_dict:
        return False
    command_name = command_name.lower().capitalize()
    if command_name in COMMANDS_ALLOWED:
        chosen_command = COMMANDS_ALLOWED[command_name](user_id, db_object, incoming_dict=data_dict,
                                                        datetime_add=datetime_add)
        return chosen_command
    else:
        return False


async def get_already_executed(operation_id, user_id, db_object):
    # Функция возвращает команду, которая ранее отправлялась на исполнение
    data = await db_object.query(Operation.query. \
                                 filter((Operation.id == operation_id) & (Operation.user_id == user_id)).statement)
    current_command = choose_command(data['command'], user_id, db_object, data)
    await current_command.define_state(data['status'])
    await current_command.get_results_from_db()
    return current_command
