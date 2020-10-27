from core.db import Base
from sqlalchemy import String, Boolean, Column


class User(Base):
    login = Column(String(50), unique=True)
    email = Column(String(256))
    info = Column(String(256))
    password = Column(String(64))
    is_active = Column(Boolean)