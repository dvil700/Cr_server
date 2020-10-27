from typing import Union, Iterable
from aiohttp.web import (HTTPNotFound, HTTPBadRequest, Request, HTTPOk, json_response, HTTPFound, HTTPMethodNotAllowed,
                         HTTPInternalServerError)
from aiohttp_jinja2 import render_template
from aiohttp_security import remember, forget
from hardware.services import AbstractDeviceCreationService, AbstractAvailableDriversInformationService
from hardware.fiscal_device_group_managers import AbstractDeviceGroupManager, DeviceAvailabilityCheck
from access_control.auth import AbstractUserManagmentService, UserExists, UserDoesNotExist
from access_control.services import AbstractAccessAdministrationService, PolicyDoesNotExist, PolicyExistsError
from apps.service_group.facades import ServiceGroupNotExists, AbstractFiscalServiceGroupFacade, ServiceGroup
from .forms import LoginForm, ServiceGroupForm, UserForm, AdminPermissionsForm
from .device_config_forms import create_fiscal_device_config_form


class ServiceGroupDescriptor:
    __slots__ = '_service_group', '_device_group_manager'

    def __init__(self, service_group: ServiceGroup, device_group_manager: DeviceAvailabilityCheck):
        self._service_group = service_group
        self._device_group_manager = device_group_manager

    @property
    def id(self):
        return self._service_group.id

    @property
    def name(self):
        return self._service_group.name

    @property
    def is_enabled(self):
        return self._service_group.is_enabled

    @property
    def driver_name(self):
        return self._service_group.settings['driver']['driver_name']

    @property
    def is_running(self):
        return self._device_group_manager.is_device_provided_for_group(self.id)


class ServiceGroupDescriptors(Iterable):
    __slots__ = ('_service_groups', '_device_group_manager')

    def __init__(self, service_groups: Iterable, device_group_manager: DeviceAvailabilityCheck):
        self._service_groups = service_groups
        self._device_group_manager = device_group_manager

    def __iter__(self):
        for service_group in self._service_groups:
            yield ServiceGroupDescriptor(service_group, self._device_group_manager)


async def login(request):
    if request.get('user'):
        return HTTPFound(location=request.app.router['index'].url_for())

    if request.method == 'POST':
        form = LoginForm(await request.post())
        if not form.validate():
            return render_template('login.html', request, context={'form':form, 'message': None})
        data = form.data
        user = await request.config_dict['authentication_service'].authenticate(data['login'].lower(), data['password'])
        request['user'] = user
        if not user:
            return render_template('login.html', request, status=400,
                                   context={'form': form, 'message':'Invalid password. Please try again'})
        response = HTTPFound(location=request.app.router['index'].url_for())
        await remember(request, response, str(user.id))
        return response
    elif request.method == 'GET':
        return render_template('login.html', request, context={'form': LoginForm(), 'message': None})
    else:
        raise HTTPMethodNotAllowed


async def logout(request):
    response = HTTPFound(location=request.app.router['login'].url_for())
    await forget(request, response)
    return response


class FiscalServicesManagementView:
    @staticmethod
    def get_fiscal_service_group_facade(request: Request) -> AbstractFiscalServiceGroupFacade:
        return request.app['fiscal_service_group_facade']

    @staticmethod
    def get_device_group_manager(request) -> Union[AbstractDeviceGroupManager, DeviceAvailabilityCheck]:
        return request.app['device_group_manager']

    @staticmethod
    def get_device_creation_service(request) -> AbstractDeviceCreationService:
        return request.app['device_creation_service']

    @staticmethod
    def get_drivers_information_service(request) -> AbstractAvailableDriversInformationService:
        return request.app['drivers_information_service']

    @staticmethod
    def get_access_service(request) -> AbstractAccessAdministrationService:
        return request.app['access_administration_service']

    def _get_drivers_list(self, request):
        available_drivers_list = self.get_drivers_information_service(request).get_available_drivers_list()
        available_drivers_list.insert(0, '')
        return list(zip(*(available_drivers_list,)*2))

    async def _get_service_group(self, request) -> ServiceGroup:
        service_group_id = request.match_info['service_group_id']
        fiscal_service_group_facade = self.get_fiscal_service_group_facade(request)
        try:
            service_group = await fiscal_service_group_facade.get_service_group(int(service_group_id))
        except ServiceGroupNotExists:
            raise HTTPNotFound
        except ValueError:
            raise HTTPBadRequest
        return service_group

    async def _get_enabled_service_group(self, request) -> ServiceGroup:
        service_group = await self._get_service_group(request)
        if not service_group.is_enabled:
            raise HTTPBadRequest(text='The service group {} is not enabled'.format(service_group.id))
        return service_group

    async def _run_fiscal_device(self, request, service_group, device_group_manager):
        if device_group_manager.is_device_provided_for_group(service_group.id):
            raise HTTPBadRequest(text='The device has been already attached to group id {}'.format(service_group.id))
        device_creation_service = self.get_device_creation_service(request)
        driver_conf = service_group.settings['driver']
        device_adapter = await device_creation_service.create_device(driver_conf['driver_name'], driver_conf['settings'])
        if not device_adapter.id:
            # Device creation service must set device id
            raise HTTPInternalServerError
        device_group_manager.add_device(service_group.id, device_adapter)
        return json_response(data={'csrf_token': request['csrf'].csrf_token.current_token})

    @staticmethod
    async def _stop_fiscal_device(request, service_group, device_group_manager):
        if not device_group_manager.is_device_provided_for_group(service_group.id):
            raise HTTPBadRequest(text='The device is not attached to group id {}'.format(service_group.id))
        await device_group_manager.detach_device(service_group.id)
        return json_response(data={'csrf_token': request['csrf'].csrf_token.current_token})

    async def fiscal_device_change_state(self, request: Request):
        data = await request.json()
        try:
            state = data.get('state').lower()
        except KeyError:
            raise HTTPBadRequest
        service_group = await self._get_enabled_service_group(request)
        device_group_manager = self.get_device_group_manager(request)
        if state == 'running':
            return await self._run_fiscal_device(request, service_group, device_group_manager)
        elif state == 'stopped':
            return await self._stop_fiscal_device(request, service_group, device_group_manager)
        else:
            raise HTTPBadRequest

    async def post_service_group(self, request: Request):
        data = await request.post()
        main_form = ServiceGroupForm(data)
        main_form.settings.driver.driver_name.choices = self._get_drivers_list(request)
        if not main_form.validate():
            return json_response(data={'errors': main_form.errors}, status=400)
        service_group_data = main_form.data
        driver_conf = service_group_data['settings']['driver']
        try:
            device_config_form = create_fiscal_device_config_form(driver_conf['driver_name'], data)
        except FileNotFoundError:
            error_message = 'The driver form with the name {} is not provided'.format(driver_conf['driver_name'])
            return json_response(data={'errors': [{'driver_name': error_message}]}, status=400)
        if not device_config_form.validate():
            return json_response(data={'errors': device_config_form.errors}, status=400)
        group_facade = self.get_fiscal_service_group_facade(request)
        service_group_data['settings']['driver']['settings'] = device_config_form.data
        service_group_id = service_group_data.get('id', None)
        if not service_group_id:
            service_group_data.pop('id', None)
            service_group = await group_facade.register_new_service_group(**service_group_data)
            service_group_id = service_group.id
        else:
            await group_facade.update_service_group_information(**service_group_data)
        return json_response(data={'service_group_id': service_group_id}, status=200)

    @staticmethod
    def _get_device_settings_form(chosen_driver_name=None, service_group=None):
        if service_group and service_group.settings['driver']['driver_name'] == chosen_driver_name:
            return create_fiscal_device_config_form(chosen_driver_name, service_group.settings['driver']['settings'])
        elif service_group and not chosen_driver_name:
            settings = service_group.settings
            return create_fiscal_device_config_form(settings['driver']['driver_name'], settings['driver']['settings'])
        elif service_group and service_group.settings['driver']['driver_name'] != chosen_driver_name:
            return create_fiscal_device_config_form(chosen_driver_name)
        elif not service_group and chosen_driver_name:
            return create_fiscal_device_config_form(chosen_driver_name)
        else:
            return tuple()

    async def get_settings_form(self, request):
        chosen_driver_name = request.match_info.get('driver_name', None)
        service_group_id = request.query.get('service_group_id', None)
        service_group = None
        if service_group_id:
            try:
                service_group_id = int(service_group_id)
            except ValueError:
                raise HTTPBadRequest
            try:
                service_group = await self.get_fiscal_service_group_facade(request).\
                    get_service_group(service_group_id)
            except ServiceGroupNotExists as e:
                service_group = None
        settings_form = self._get_device_settings_form(chosen_driver_name, service_group)
        return render_template('service_group_settings.html', request=request, context={'device_config_form':settings_form})

    async def get_existing_service_group_form(self, request):
        service_group = await self._get_service_group(request)
        main_form = ServiceGroupForm.from_json(service_group.as_dict())
        main_form.settings.driver.driver_name.choices = self._get_drivers_list(request)
        device_config_form = self._get_device_settings_form(None, service_group)
        context = {'main_form': main_form, 'device_config_form': device_config_form}
        return render_template('service_group_settings.html', request=request, context=context)

    async def get_new_service_group_form(self, request):
        main_form = ServiceGroupForm()
        main_form.settings.driver.driver_name.choices = self._get_drivers_list(request)
        context = {'main_form': main_form, 'device_config_form': tuple()}
        return render_template('service_group_settings.html', request=request, context=context)

    async def get_service_groups(self, request):
        facade = self.get_fiscal_service_group_facade(request)
        service_groups = ServiceGroupDescriptors(await facade.get_service_groups(), self.get_device_group_manager(request))
        return render_template('service_group.html', request=request, context=dict(service_groups=service_groups))

    async def delete_service_group(self, request):
        service_group_id = int(request.match_info['service_group_id'])
        facade = self.get_fiscal_service_group_facade(request)
        resource_prefix = '_'.join(('service_group', str(service_group_id)))
        await self.get_access_service(request).delete_resource_access_data(resource_prefix)
        device_group_manager = self.get_device_group_manager(request)
        if device_group_manager.is_device_provided_for_group(service_group_id):
            await device_group_manager.detach_device(service_group_id)
        await facade.delete_service_group(service_group_id)
        return HTTPOk()


class BaseAccessManagementView:
    @staticmethod
    def get_users_management_service(request) -> AbstractUserManagmentService:
        return request.app['user_management_service']

    @staticmethod
    def get_access_service(request) -> AbstractAccessAdministrationService:
        return request.app['access_administration_service']


class UsersView(BaseAccessManagementView):
    @staticmethod
    def get_admin_resource_id(request) -> str:
        return request.app['admin_access_attr_calc_strategy'].get_resource_id(request)

    @staticmethod
    def get_admin_context(request) -> dict:
        return request.app['admin_access_attr_calc_strategy'].get_context(request)

    async def get_users(self, request):
        access_service = self.get_access_service(request)
        admin_app_id = self.get_admin_resource_id(request)
        admin_users = await access_service.get_resource_access_settings(admin_app_id)
        admins_user_id_set = set(map(lambda x: x.user_id, admin_users))
        users_service = self.get_users_management_service(request)
        users = await users_service.get_users('id', 0, 100)
        return render_template('users.html', request=request, context=dict(users=users, admins=admins_user_id_set))

    async def get_user_form(self, request: Request):
        users_service = self.get_users_management_service(request)
        user_id = request.match_info.get('user_id')
        if user_id:
            try:
                user = await users_service.get_user(int(user_id))
            except ValueError:
                raise HTTPBadRequest
            user_form = UserForm(user_id=user_id, **user._asdict())
            access_service = self.get_access_service(request)
            try:
                admin_resource_id = self.get_admin_resource_id(request)
                permissions = (await access_service.get_resource_access_settings(admin_resource_id, str(user_id)))[0]
            except IndexError:
                admin_permissions_form = AdminPermissionsForm()
            else:
                admin_permissions_form = AdminPermissionsForm(**permissions._asdict())
        else:
            user_form = UserForm()
            admin_permissions_form = AdminPermissionsForm()
        return render_template('user_form.html', request=request, context=dict(user_form=user_form,
                                                                               permissions_form=admin_permissions_form))

    async def post_user_form(self, request: Request):
        access_service = self.get_access_service(request)
        users_service = self.get_users_management_service(request)
        resource_id = self.get_admin_resource_id(request)
        user_id = request.match_info.get('user_id')
        data = await request.post()
        user_form = UserForm(data)
        admin_permissions_form = AdminPermissionsForm(data)
        if not user_form.validate() or not admin_permissions_form.validate():
            context = dict(user_form=user_form, permissions_form=admin_permissions_form)
            return render_template('user_form.html', request=request, context=context, status=400)
        user_data = user_form.data
        del user_data['password_repeat']
        if user_id:
            await users_service.update_user(user_id=int(user_id), **user_data)
            await access_service.unset_access_policy(user_id, resource_id)

        else:
            try:
                user = await users_service.create_new_user(**user_data)
            except UserExists:
                user_form.login.errors.append('Пользователь с логином {} уже существует'.format(user_data['login']))
                context = dict(user_form=user_form, permissions_form=admin_permissions_form)
                return render_template('user_form.html', request=request, context=context, status=400)

            user_id = str(user.id)
        permissions_data = admin_permissions_form.data
        if any(permissions_data.values()):
            await access_service.set_access_policy(user_id, resource_id, **permissions_data)
        return HTTPOk()

    async def delete_user(self, request: Request):
        access_service = self.get_access_service(request)
        users_service = self.get_users_management_service(request)
        user_id = request.match_info.get('user_id')
        if not user_id:
            raise HTTPBadRequest(text='The user id is unset')
        try:
            await users_service.delete_user(int(user_id))
        except UserDoesNotExist:
            raise HTTPBadRequest(text='The user {} does not exist'.format(user_id))
        await access_service.delete_user_access_data(user_id)
        return HTTPOk()


class ServiceGroupAccessView(BaseAccessManagementView):
    async def get_service_group_allowed_users(self, request):
        service_group_id = request.match_info['service_group_id']
        users_service = self.get_users_management_service(request)
        access_service = self.get_access_service(request)
        resource_access_settings = await access_service.get_resource_access_settings('_'.join(('service_group',
                                                                                               service_group_id)))
        all_users = await users_service.get_users('id', 0, 100)
        resource_users = {item.user_id: '' for item in resource_access_settings}
        context = {'all_users': all_users, 'resource_users': resource_users, 'service_group_id':service_group_id}
        return render_template('service_group_access_settings.html', request=request, context=context)

    async def post_service_group_allowed_users(self, request):
        service_group_id = request.match_info['service_group_id']
        users_service = self.get_users_management_service(request)
        access_service = self.get_access_service(request)
        resource_prefix = '_'.join(('service_group', service_group_id))
        resource_access_settings = await access_service.get_resource_access_settings(resource_prefix)
        resource_users_before = {item.user_id for item in resource_access_settings}

        data = await request.json()
        for user_id in data['resource_users']:
            user_id = str(user_id)
            if user_id in resource_users_before or not (await users_service.get_user(int(user_id))):
                resource_users_before.remove(user_id)
                continue
            await access_service.set_access_policy(user_id, resource_prefix, True, True, True)

        for user_id in resource_users_before:
            await access_service.unset_access_policy(user_id, resource_prefix)

        return HTTPOk()








'''
def reboot_fiscal_device(request): #view
    sg_id = service_group_id = request.match_info['service_group_id']
    device_group_manager = request['config_dict']['fiscal_device_group_manager'](service_group_id)
    if not self.is_device_provided_for_group(sg_id):
        raise DeviceIsNotRunning('The device is not attached to service group id {}'.format(sg_id))
    await device_group_manager.pause_command_execution(sg_id)
    await device_group_manager.reboot(sg_id)
    await device_group_manager.close_device(sg_id)
    new_device_adapter = await request['config_dict']['device_adapter_factory'].create_adapter(driver_conf['settings'])
    await device_group_manager.replace_device(sg_id, new_device_adapter)
    await device_group_manager.resume_command_execution(sg_id) '''
