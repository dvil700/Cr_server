from db.model import Base
from abc import ABC, abstractmethod
from sqlalchemy import Integer, String, Boolean, Column, Table, ForeignKey, UniqueConstraint, case, literal_column
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.attributes import InstrumentedAttribute
from multidict import MultiDict

user_permission = Table('user_permission', Base.metadata,
                        Column('user', Integer, ForeignKey('user.id')),
                        Column('permission', Integer, ForeignKey('permission.id')),
                        )

user_group = Table('user_group', Base.metadata,
                   Column('user_id', Integer, ForeignKey('user.id')),
                   Column('group_id', Integer, ForeignKey('group.id')),
                   )

group_permission = Table('group_permission', Base.metadata,
                         Column('id', Integer, primary_key=True),
                         Column('group', Integer, ForeignKey('group.id')),
                         Column('permission', Integer, ForeignKey('permission.id')),
                         )


class AbstractUser(ABC):

    @property
    @abstractmethod
    def user_id(self):
        pass

    @property
    @abstractmethod
    def login(self):
        pass

    @property
    @abstractmethod
    def is_authenticated(self):
        pass

    @abstractmethod
    async def get_permissions(self):
        pass

    @abstractmethod
    async def get_group_permissions(self):
        pass

    @abstractmethod
    async def get_user_permissions(self):
        pass

    async def has_permission(self, permission):
        permissions = await self.get_permissions()
        return getattr(self, 'enabled', False) and permission in permissions


class RelationsMixin:
    def is_enabled_column(self, column=None):
        column_enabled = literal_column('0').label('is_enabled')
        if self.id:
            column_enabled = case([(column == self.id, 'checked'), ], else_='').label('is_enabled')
        return column_enabled

    async def get_relations(self, rel_attr: InstrumentedAttribute, conn, checked_relations=set()):
        # Метод реализует логику получения данных из моделей о взаимосвязях конкретного пользователя и групп,
        # пользователя и его разрешений, конкретной группы и её разрешений.
        # rel_attr - User.groups, User.permissions и т.д.
        relations_table = rel_attr.property.secondary
        ident_col, rel_col = tuple((item[1] for item in rel_attr.prop.local_remote_pairs))
        column_enabled = self.is_enabled_column(ident_col)
        general_model = rel_attr.prop.mapper.class_
        sql = general_model.query.outerjoin(relations_table, ((rel_col==general_model.id) & (ident_col == self.id))). \
            with_entities(general_model.id.label('id'), general_model.name.label('name')).add_column(column_enabled). \
            statement.apply_labels()
        relations_from_db = await conn.query(sql, rows=True)

        if len(checked_relations)>0:
            for i, relation in enumerate(relations_from_db):
                relations_from_db[i] = relation = dict(relation)  # RowProxy неизменяемый, поэтому преобразуем в dict
                relation['is_enabled'] = 'checked' if str(relation['id']) in checked_relations else 0

        return relations_from_db

    async def add_relations(self, rel_attr: InstrumentedAttribute, data: MultiDict, conn):
        # rel_attr - атрибут связи many to many (например User.groups, User.permissions)
        relations_table = rel_attr.property.secondary  # класс таблицы связей many-to-many
        ident_col, rel_col = tuple((item[1] for item in rel_attr.prop.local_remote_pairs))
        # rel_attr.prop.local_remote_pairs - список кортежей (по 2 элемента) связей таблиц
        relations = [{'id': None, ident_col.name: self.id, rel_col.name: rel_id} for rel_id in
                     data.getall(rel_col.name, [])]
        await conn.execute(relations_table.delete(ident_col == self.id))
        if len(relations) == 0:
            return
        await conn.execute(relations_table.insert(), relations)


class User(RelationsMixin, Base):
    login = Column(String(50))
    passwd = Column(String(64))
    superuser = Column(Boolean, default='False')
    enabled = Column(Boolean)
    groups = relationship("Group", secondary=user_group,
                          backref=backref("users", lazy="dynamic"))

    permissions = relationship("Permission", secondary=user_permission,
                               backref=backref("users", lazy="dynamic"))
    unique_user = UniqueConstraint('login')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_authenticated = False

    @property
    def is_authenticated(self):
        return True

    @property
    def user_id(self):
        return self._id

    def get_permissions(self):
        return self._get_fozenset(self._get_group_permissions().union(self._get_user_permissions()))

    def get_group_permissions(self):
        return self._get_fozenset(self._get_group_permissions())

    def get_user_permissions(self):
        return self._get_fozenset(self._get_user_permissions())

    async def _get_fozenset(self, sql_request):
        results = await self.conn.query(sql_request, rows=True)
        return frozenset([result[0] for result in results])

    def _get_group_permissions(self):
        return self.query.join(User.groups).join(Group.permissions).filter(User.id == self.id). \
            with_entities(Permission.name).statement.apply_labels()

    def _get_user_permissions(self):
        return self.query.join(User.permissions).filter(User.id == self.id). \
            with_entities(Permission.name).statement.apply_labels()


class Group(RelationsMixin, Base):
    name = Column('name', String(50))
    unique_group = UniqueConstraint('name')


class Permission_type(Base):
    name = Column(String(50), nullable=None)
    unique_permission_type = UniqueConstraint('name')


class Permission(Base):
    name = Column(String(50))
    permission_type_id = Column(Integer, ForeignKey('permission_type.id', ondelete="CASCADE"), nullable=False)
    root_app_name = Column(String(50))
    groups = relationship("Group", secondary=group_permission,
                          backref=backref("permissions", lazy="dynamic"))

    @classmethod
    async def insert(cls, resources):
        # Решение для mysql с Ignore
        await cls.conn.query(cls.__table__.insert().prefix_with('IGNORE'), resources)


class UserProxy(AbstractUser):

    def __init__(self, user_object):
        self.user_object = user_object
        self._cache = {}

    def __getattr__(self, key):
        return getattr(self.user_object, key)

    @property
    def user_id(self):
        return self.user_object.user_id

    @property
    def is_authenticated(self):
        return self.user_object.is_authenticated

    @property
    def login(self):
        return self.user_object.login

    async def get_permissions(self):
        cache = self._cache
        if 'united_permissions' in cache:
            return cache['united_permissions']

        user_permissions = cache.get('user_permissions', False)
        group_permissions = cache.get('group_permissions', False)

        if not user_permissions and not group_permissions:
            cache['united_permissions'] = await self.user_object.get_permissions()
            return cache['united_permissions']

        if not user_permissions:
            user_permissions = await self.get_user_permissions()

        if not group_permissions:
            group_permissions = await self.get_group_permissions()

        cache['united_permissions'] = frozenset(user_permissions.union(group_permissions))

        return cache['united_permissions']

    def get_user_permissions(self):
        return self._get_perms_using_cache('user_permissions', self.user_object.get_user_permissions())

    def get_group_permissions(self):
        return self._get_perms_using_cache('group_permissions', self.user_object.get_group_permissions())

    async def _get_perms_using_cache(self, key, base_method):
        if not self._cache.get(key, False):
            self._cache[key] = await base_method()
        return self._cache[key]


class Guest(AbstractUser):

    @property
    def user_id(self):
        return None

    @property
    def login(self):
        return None

    @property
    def is_authenticated(self):
        return False

    async def get_permissions(self):
        return frozenset()

    async def get_group_permissions(self):
        return frozenset()

    async def get_user_permissions(self):
        frozenset()
