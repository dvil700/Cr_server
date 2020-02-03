from db.model import Base
from sqlalchemy import Column, String, Integer, TIMESTAMP, ForeignKey, SmallInteger, UniqueConstraint, Index
from sqlalchemy import Text, DECIMAL, Enum as SAEnum
import enum
from datetime import datetime


class Enum(bytes, enum.Enum):
    def __new__(cls, value, text):
        obj = bytes.__new__(cls, [value])
        obj._value_ = value
        obj.text = text
        return obj

    def __str__(self):
        return self.text


class CommandStates(Enum):
    # Поля должны соответствовать именам классов состояний в в нижнем регистре из states.py
    inproccess = (0, 'В процессе')
    success = (1, 'Выполнено успешно')
    withwarning = (2, 'Выполнено с предупреждением')
    fail = (3, 'Не выполнено')


class Operation(Base):
    command = Column(String(20))
    user_id = Column(Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    client_operation_id = Column(Integer, nullable=False)
    client_operation_datetime = Column(TIMESTAMP, nullable=True)
    datetime_add = Column(TIMESTAMP, nullable=True)
    datetime_modify = Column(TIMESTAMP, default=datetime.utcnow, nullable=True)
    state = Column(SAEnum(CommandStates), nullable=False)
    result = Column(Text)
    errors = Column(Text)
    unique_command = UniqueConstraint('user_id', 'client_operation_id', 'client_operation_datetime')
    client_operation = Index('user_id', 'client_operation_id')

    @classmethod
    async def get_proccessed_operation_id(cls, user_id, client_operation_id, client_operation_datetime, db_conn):
        sql = cls.query.filter((cls.user_id == user_id) &
                               (cls.client_operation_id == client_operation_id) &
                               (cls.client_operation_datetime == client_operation_datetime)). \
            with_entities(cls.id).statement
        data = await db_conn.query(sql)
        if data:
            return data[0]


class CrMixin:
    # Mixin для добавления функциональности всем моделям, связанным с данными о кассовой технике и регистрационными
    # данными из памяти онлайн кассы

    _secondary_fields = set()  # названия полей, значения которых разрешено менять в одной записи (без создания новой).

    # Если меняется значение полей не из _secondary_fields , то должна создаваться новая запись в бд, т.к. эти данные
    # не могут быть изменены (в соответствии с законодателством) в уже зарегистрированной фискальной операции.

    @classmethod
    async def register_and_get(cls, conn, **kw):
        # те параметры, ключи которых лежат в _secondary_fields  не "идентифицирюут" записи, и могут меняться
        # в рамках существующих записей (без создания новой).
        # Остальные элементы используются для построения sql выражения фильтрации данных
        # (ключ - имя атрибута модели, значение есть искомое значение).
        # filter_exp - переменная для хранения выражений для фильтрации
        filter_exp = None
        for key, item in kw.items():
            if key in cls._secondary_fields:
                continue
            # тип полученного значения переменной exp будет sqlalchemy BinaryExpression
            exp = (getattr(cls, key) == item)
            # тип полученного значения переменной  filter exp будет sqlalchemy BooleanClauseList в случае если пришло
            # больше одного параметра
            filter_exp = exp if not filter_exp else filter_exp & exp

        obj = await cls.get_object(conn, filter_exp)

        if not obj:
            obj = cls(**kw)
            obj.id = (await conn.execute(obj.add())).lastrowid
        elif len(cls._secondary_fields) > 0:
            # если запись найдена (создан объект модели) и есть дополнительные данные, смотрим изменились ли они, если
            # что-то изменилось, обновляем запись в базе
            changes = None
            for key in cls._secondary_fields:
                attr = getattr(obj, key)
                if attr is not kw[key]:
                    attr = kw[key]
                    changes = True
            if changes:
                await conn.execute(obj.update)

        return obj


class IncomeData(CrMixin, Base):
    operation_id = Column(Integer, ForeignKey('operation.id', ondelete='CASCADE'), nullable=False)
    data = Column(Text, nullable=False)


class CrHardware(CrMixin, Base):
    # Кассовые аппараты
    serial_number = Column(String(30))
    # регистрационный номер в налоговой:
    registration_number = Column(String(30))
    unique_registration_number = UniqueConstraint('registration_number')


class CashRegister(CrMixin, Base):
    # Конкретная касса с фискальным накопителем
    fn_serial = Column(String(30))
    cr_hardware_id = Column(Integer, ForeignKey('crhardware.id', ondelete='CASCADE'), nullable=False)
    unique_fn_serial = UniqueConstraint('fn_serial')


class Ofd(CrMixin, Base):
    name = Column(String(50))
    url = Column(String(50))
    inn = Column(String(12))
    unique_ofd_name = UniqueConstraint('name')

    _secondary_fields = {'url'}


class Company(CrMixin, Base):
    name = Column(String(50))
    inn = Column(String(12))
    email = Column(String(50))
    address = Column(String(50))
    payment_addr = Column(String(50))

    _secondary_fields = {'address', 'email', 'payment_addr'}


class OnlineCR(CrMixin, Base):
    # Онлайн-касса прикрепленная к ОФД и компании, с определенной версией ффд
    cash_register_id = Column(Integer, ForeignKey('cashregister.id', ondelete='CASCADE'), nullable=False)
    ofd_id = Column(Integer, ForeignKey('ofd.id', ondelete='CASCADE'))
    ffd_version = Column(SmallInteger, nullable=False)
    company_id = Column(Integer, ForeignKey('company.id', ondelete='CASCADE'), nullable=False)

    @classmethod
    def get_cr_data_joins(cls, saquery):
        # saquery - sqlalchemy query object
        return saquery.join(CashRegister).join(CrHardware).join(cls.Ofd).join(cls.Company)


class DocumentTypes(Enum):
    doc_registration = (1, 'Отчет о регистрации')
    doc_open_shift = (2, 'Отчет об открытии смены')
    doc_receipt = (3, 'Кассовый чек')
    doc_bso = (4, 'Бланк строгой отчетности')
    doc_close_shift = (5, 'Отчет о закрытии смены')
    doc_close_fn = (6, 'Отчет о закрытии фискального накопителя')
    doc_operator_confirmation = (7, 'Подтверждение оператора')
    doc_reregistration = (11, 'Отчет об изменении параметров регистрации')
    doc_exchange_status = (21, 'Отчет о текущем состоянии расчетов')
    doc_correction = (31, 'Кассовый чек коррекции')
    doc_bso_correction = (41, 'Бланк строгой отчетности коррекции')


class ReceiptType(Enum):
    rt_sell = (1, 'чек прихода (продажи)')
    rt_sell_return = (2, 'чек возврата прихода (продажи)')
    rt_sell_correction = (7, 'чек коррекции прихода (продажи)')
    rt_sell_return_correction = (8, 'чек коррекции возврата прихода')
    rt_buy = (4, 'чек расхода (покупки)')
    rt_buy_return = (5, 'чек возврата расхода (покупки)')
    rt_buy_correction = (9, 'чек коррекции расхода (покупки)')
    rt_buy_return_correction = (10, 'чек коррекции возврата расхода')


class FiscalDocument(Base):
    operation_id = Column(Integer, ForeignKey('operation.id', ondelete='CASCADE'), nullable=False)
    documentNumber = Column(Integer, nullable=False)
    receiptType = Column(SAEnum(ReceiptType), nullable=False)
    fiscalSign = Column(String(20), nullable=False)
    documentDate = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    document_summ = Column(DECIMAL(10, 2), default=0)
    online_cr_id = Column(Integer, ForeignKey('onlinecr.id'), nullable=False)
