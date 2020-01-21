from aiohttp import web
import aiohttp_jinja2
from aiohttp_security.api import forget, remember
from auth.models import User, Group, Permission, Permission_type
from .forms import LoginFormRedirectable, LoginForm, UserForm, GroupForm, PasswdForm, NewUserForm
from sqlalchemy import case
from cr_server.pagination import Paginator
from commands.models import Operation, FiscalDocument, CashRegister, OnlineCR, Company, CrHardware, Ofd
from . import texts
from abc import ABC, abstractmethod
from forms.form import Form
from multidict import MultiDictProxy


async def login_handler(request):
    if request['user'].is_authenticated:
        return web.HTTPFound(request.app.router['main'].url_for())
    if request.get('redirected_to_login', None):
        form = LoginFormRedirectable(redirect=request.path_qs)
        context = {'form': form}
        return aiohttp_jinja2.render_template('login.html',
                                              request, context)
    return await LoginView(request)


class LoginView(web.View):
    async def get(self):
        form = LoginForm()
        return self._render(form)

    async def post(self):
        parameters = await self.request.post()
        form = LoginForm(parameters)
        if not form.validate():
            return self._render(form)
        user = await auth(form.data['login'], form.data['passwd'])
        if not user.is_authenticated:
            form.set_auth_error()
            return self._render(form)

        redirect_url = self.request.get('redirect', self.request.app.router['main'].url_for())
        response = web.HTTPFound(redirect_url)

        await remember(self.request, response, str(user.id))
        self.request['user'] = user
        return response

    def _render(self, form):
        context = {'a': 'login', 'b': 'sdfsadf', 'form': form}
        return aiohttp_jinja2.render_template('login.html',
                                              self.request, context)


async def logout_handler(request):
    redirect_response = web.HTTPFound(request.app.router['login'].url_for())
    await forget(request, redirect_response)
    raise redirect_response


async def index_handler(request):
    context = {}
    response = aiohttp_jinja2.render_template('other_content.html', request, context)
    return response


class ListView(web.View, ABC):
    @property
    @abstractmethod
    def template(self) -> str:
        pass # ex. return 'list.html'

    @property
    @abstractmethod
    def sql(self):
        pass

    async def _render(self, sql, template=None, **kw):
        page_num = self.request.query.get('page', 1)
        paginator = Paginator(sql, 20, self.request.config_dict['db'])
        page = await paginator.page(page_num)
        context = dict(theaders=self.table_headers, page=page, **kw)
        if not template:
            template = self.template
        return aiohttp_jinja2.render_template(template, self.request, context)

    async def get(self):
        return await self._render(self.sql)


class UserListView(ListView):
    @property
    def template(self):
        return 'list_form.html'

    @property
    def table_headers(self) -> tuple:
        return texts.users_list_headers

    @property
    def sql(self):
        is_enabled = case([(User.enabled == True, 'Включен'), ], else_='').label('is_enabled')
        is_superuser = case([(User.superuser == True, 'Да'), ], else_='').label('is_superuser')
        return User.query.with_entities(User.id, User.login).add_columns(is_enabled, is_superuser)

    async def get(self):
        return await self._render(self.sql, checkboxes_allowed=True, column_actions=dict(change=True))

class GroupListView(ListView):
    @property
    def template(self):
        return 'list_form.html'

    @property
    def table_headers(self) -> tuple:
        return texts.groups_list_headers

    @property
    def sql(self):
        return Group.query.with_entities(Group.id, Group.name)

    async def get(self):
        return await self._render(self.sql, checkboxes_allowed=True, column_actions=dict(change=True))


async def simple_list_render(request, sql, table_headers, template=None, **kw):
    page_num = request.query.get('page', 1)
    paginator = Paginator(sql, 20, request.config_dict['db'])
    page = await paginator.page(page_num)
    context = dict(theaders=table_headers, page=page, **kw)
    if not template:
        template = 'list.html'
    return aiohttp_jinja2.render_template(template, request, context)


async def permissions_list(request):
    pm = Permission
    sql = pm.query.join(Permission_type).with_entities(pm.id, pm.name, Permission_type.name). \
        filter(pm.root_app_name == request.config_dict['cr_app_name']).order_by(pm.name.asc())
    return await simple_list_render(request, sql, texts.permission_list_headers)


class OperationsListView(ListView):
    @property
    def template(self):
        return 'list_simple.html'

    @property
    def table_headers(self) -> tuple:
        return texts.operation_list_headers

    @property
    def sql(self):
        op = Operation
        return op.query.join(User).with_entities(op.id, op.command, User.login, op.client_operation_id, op.datetime_add,
                                                 op.datetime_modify, op.state).order_by(op.id.desc())

    async def get(self):
        return await self._render(self.sql, checkboxes_allowed=False)


class FiscalDocumentsListView(ListView):
    @property
    def template(self):
        return 'list_simple.html'

    @property
    def table_headers(self) -> tuple:
        return texts.fiscal_document_list_headers

    @property
    def sql(self):
        fd = FiscalDocument
        sql = fd.query.join(OnlineCR).join(CashRegister).join(CrHardware).join(Ofd).join(Company). \
            with_entities(fd.id, fd.operation_id, fd.documentType, fd.documentNumber, fd.receiptType, fd.fiscalSign,
                          fd.documentDate, fd.document_summ, CrHardware.serial_number, CashRegister.fn_serial,
                          Ofd.name).order_by(fd.id.desc())
        return sql

    async def get(self):
        return await self._render(self.sql, checkboxes_allowed=False)


class ScrollBoxItem(dict):
    def __init__(self, name, text, vals):
        self.name = self['name'] = name
        self.text = self['text'] = text
        self.vals = self['vals'] = vals


class ScrollBoxList(list):
    def append(self, *args) -> None:
        super().append(ScrollBoxItem(*args))


class HasIdentMixin:
    @property
    def ident(self):
        ident = self.request.match_info['ident']
        try:
            int(ident)
        except ValueError:
            if ident != 'new':
                raise web.HTTPNotFound()
            ident = None
        return ident


class StaffView(web.View, HasIdentMixin, ABC):
    # Родитель для UserView и GroupView
    @property
    @abstractmethod
    def table_cls(self):
        # Класс модели, содержащей информацию о целевом объекте БД (например User или Group)
        pass

    async def get_staff_data(self):
        # метод достает из базы данные об объекте персонала (например о пользователе, либо группе, что зависит от
        # конкретной реализации) с идентификатором self.id
        data = await self.request.config_dict['db'].query(
            self.table_cls.query.filter(self.table_cls.id == self.ident).statement)
        return data

    async def get_permissions(self, ident=None):
        model = self.table_cls
        return await model(id=self.ident).get_relations(model.permissions, self.request.config_dict['db'])

    @property
    def sboxes_list(self):
        # Список для формирования scroll_box форм (разрешения пользователя и группы, связи для групп и пользователей)
        if not getattr(self, '_sboxes_list', None):
            self._sboxes_list = ScrollBoxList()
        return self._sboxes_list

    @abstractmethod
    async def scroll_boxes_create(self, post_data: list = []):
        # Создаем необходимый для конкретной view набор scroll_box форм
        pass

    @abstractmethod
    def render(self, form: Form) -> web.Response:
        pass

    async def post(self):
        post_data = await self.request.post()
        form = self.post_form_factory(post_data)
        if not form.validate():
            await self.scroll_boxes_create()
            return self.render(form)
        await self._post_transaction(form, post_data)
        return web.HTTPFound(self.request.app.router[self.table_cls.__name__.lower() + 's'].url_for())

    @abstractmethod
    def post_form_factory(self, post_data: MultiDictProxy) -> Form:
        pass

    async def _post_transaction(self, form, postdata):
        async with self.request.config_dict['db'].conn as conn:
            transaction = await conn.begin()
            try:
                await self._post_transaction_logic(transaction, form, postdata)
            except Exception as e:
                await transaction.rollback()
                raise e
                # raise web.HTTPBadRequest
            await transaction.commit()

    @abstractmethod
    async def _post_transaction_logic(self, transaction, form, postdata):
        # Логика post запроса, работающая с транзакцией бд
        pass


class UserView(StaffView):
    @property
    def table_cls(self):
        return User

    async def scroll_boxes_create(self):
        post_data = await self.request.post()
        # отмеченные в форме разрешения:
        permissions_checked = set(post_data.getall('permission', []))
        self.sboxes_list.append('permission', 'Разрешения', await self.get_permissions(permissions_checked))
        # отмеченные в форме группы:
        groups_checked = set(post_data.getall('group_id', []))
        groups = await User(id=self.ident).get_relations(User.groups, self.request.config_dict['db'], groups_checked)
        self.sboxes_list.append('group_id', 'Группы', groups)

    def render(self, form):
        context = {'scroll_boxes': self.sboxes_list, 'url_name': 'user', 'ident': self.ident, 'form': form,
                   'additional': 'userview_pass_section.html'}
        return aiohttp_jinja2.render_template('stuff_form.html', self.request, context)

    async def get(self):
        await self.scroll_boxes_create()
        if self.ident:
            user_data = await self.get_staff_data()
            if not user_data:
                raise web.HTTPNotFound()
            form = UserForm(**user_data)
        else:
            form = NewUserForm()
        return self.render(form)

    def post_form_factory(self, post_data):
        if self.ident:
            userform = UserForm(post_data)
        else:
            userform = NewUserForm(post_data)
        return userform

    async def _post_transaction_logic(self, transaction, form, post_data):
        conn = transaction.connection
        user_data = form.data.copy()
        user = User(id=self.ident, **user_data)
        if self.ident:
            await conn.execute(user.update)
        else:
            user.id = (await conn.execute(user.add())).lastrowid
        await user.add_relations(User.permissions, post_data, conn)
        await user.add_relations(User.groups, post_data, conn)


class GroupView(StaffView):

    @property
    def table_cls(self):
        return Group

    def render(self, form):
        context = {'scroll_boxes': self.sboxes_list, 'url_name': 'group', 'ident': self.ident, 'form': form}
        return aiohttp_jinja2.render_template('stuff_form.html', self.request, context)

    async def scroll_boxes_create(self):
        post_data = await self.request.post()
        # отмеченные в форме разрешения:
        permissions_checked = set(post_data.getall('permission', []))
        self.sboxes_list.append('permission', 'Разрешения', await self.get_permissions(permissions_checked))

    async def get(self):
        await self.scroll_boxes_create()
        if self.ident:
            group_data = await self.get_staff_data()
            if not group_data:
                raise web.HTTPNotFound()
            form = GroupForm(**group_data)
        else:
            form = GroupForm()
        return self.render(form)

    def post_form_factory(self, post_data):
        return GroupForm(post_data)

    async def _post_transaction_logic(self, transaction, form, post_data):
        conn = transaction.connection
        group_data = form.data
        group = Group(id=self.ident, **group_data)
        if self.ident:
            await conn.execute(group.update)
        else:
            group.id = (await conn.execute(group.add())).lastrowid

        await group.add_relations(Group.permissions, post_data, conn)


class ChangePassView(web.View, HasIdentMixin):
    async def get(self):
        passwdform = PasswdForm()
        return aiohttp_jinja2.render_template('change_pass_form.html', self.request, {'ident': self.ident,
                                                                                      'passwdform': passwdform})