from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Query
from sqlalchemy import Integer, Column, update as sa_update, Enum as SAEnum


class Model:
    def __init__(self, db_object=None):
        self._db = db_object


class ConnectionDescriptor:
    def __get__(self, instance, owner):
        return owner.metadata.bind


class TablenameDescriptor:
    def __get__(self, instance, owner):
        return owner.__name__.lower()


class QueryDescriptor:
    def __get__(self, instance, owner):
        return Query(owner)


class Update:
    def __get__(self, instance, owner):
        if instance:
            return sa_update(owner).values(**instance.get_value_dict()).where(owner.id == instance.id)
        return sa_update(owner)


class SABaseExtension:
    __tablename__ = TablenameDescriptor()
    conn = ConnectionDescriptor()
    id = Column(Integer, primary_key=True)
    query = QueryDescriptor()

    update = Update()

    def add(self):
        return self._add()

    async def add_now(self):
        self.id = await self.conn.query(self._add())

    @classmethod
    async def get_object(cls, db_conn, exp):
        params = await (await (db_conn.execute(cls.query.filter(exp).statement))).fetchone()
        if params:
            return cls(**params)

    def get_value_dict(self):
        value_dict = {}
        keys = self.__table__.columns.keys()
        for key in keys:
            value = getattr(self, key)
            if getattr(self, key) is None:
                continue
            column = getattr(self.__table__.c, key)
            if isinstance(column.type, SAEnum):
                value = self.enum_process(column, value)
            value_dict[key] = value
        return value_dict

    def enum_process(self, column, value):
        if isinstance(value, int):
            return column.type.enum_class(value)
        return value

    def _add(self):
        request = self.__table__.insert().values(**self.get_value_dict())
        return request
    # Query(User).join(User.groups)


Base = declarative_base(cls=SABaseExtension)
