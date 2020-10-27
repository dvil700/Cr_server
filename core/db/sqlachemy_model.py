from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer


class TablenameDescriptor:
    def __get__(self, instance, owner):
        return owner.__name__.lower()


class BaseExtention:
    __tablename__ = TablenameDescriptor()
    id = Column(Integer, primary_key=True)


Base = declarative_base(cls=BaseExtention)