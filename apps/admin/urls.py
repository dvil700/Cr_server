from aiohttp import web
from apps.admin.view import FiscalServicesManagementView, UsersView, login, logout, ServiceGroupAccessView


def get_routes():
    view = FiscalServicesManagementView()
    users_view = UsersView()
    sg_access_view = ServiceGroupAccessView()
    return [web.get('/', view.get_service_groups, name='index'),
            web.get('/login/', login, name='login'),
            web.post('/login/', login, name='login'),
            web.get('/logout/', logout, name='logout'),
            web.get('/service_groups/new', view.get_new_service_group_form, name='new_service_group'),
            web.post('/service_groups/', view.post_service_group, name='post_service_group'),
            web.get('/service_groups/{service_group_id}', view.get_existing_service_group_form,
                    name='service_group_settings'),
            web.post('/service_groups/{service_group_id}', view.post_service_group),
            web.delete('/service_groups/{service_group_id}', view.delete_service_group),
            web.get('/driver_forms/{driver_name}', view.get_settings_form, name='driver_forms'),
            web.post('/service_groups/{service_group_id}/fiscal_device/', view.fiscal_device_change_state),
            web.get('/service_groups/{service_group_id}/allowed_users/', sg_access_view.get_service_group_allowed_users,
                    name='service_group_allowed_users'),
            web.post('/service_groups/{service_group_id}/allowed_users/',
                     sg_access_view.post_service_group_allowed_users, name='post_service_group_allowed_users'),
            web.get('/users/', users_view.get_users, name='users'),
            web.get('/users/new', users_view.get_user_form, name='new_user'),
            web.get('/users/{user_id}', users_view.get_user_form, name='user_settings'),
            web.delete('/users/{user_id}', users_view.delete_user),
            web.post('/users/', users_view.post_user_form),
            web.post('/users/{user_id}', users_view.post_user_form, name='post_user_form')]