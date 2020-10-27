from core.db import Base
from sqlalchemy import Column, Boolean, String, JSON


class ServiceGroup(Base):
    name = Column(String(20), default=True, nullable=False, unique=True)
    is_enabled = Column(Boolean(20), default=True, nullable=False)
    settings = Column(JSON, default={})


