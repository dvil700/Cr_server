from auth.auth import auth
import re
from .models import Permission, Permission_type

__all__ = ['auth', 'register_route_permissions', 'get_perm_entry']


async def register_route_permissions(app):
    # регистрируем права на доступ к url адресам приложения в базе данных
    resources = set()
    queue = []
    methods = ('get', 'post', 'delete')
    for resource in app.router.resources():
        queue.append(resource)
        while len(queue) > 0:
            item = queue.pop(0)
            if item.name in ('login', 'logout'):
                continue
            sub_app = item.get_info().get('app', None)
            if sub_app:
                for rs in sub_app.router.resources():
                    queue.append(rs)
            else:
                path = get_perm_entry(app, item.canonical)
                resources.update(set(['__'.join((path, meth)) for meth in methods]))

    pm_type_path = await Permission_type.conn.query(
        Permission_type.query.filter(Permission_type.name == 'path').statement)
    if not pm_type_path:
        pm_type_path = await Permission_type.conn.query(Permission_type(name='path').add())
    else:
        pm_type_path = pm_type_path[0]
    perm_from_db = await Permission.conn.query(Permission.query. \
                                               filter((Permission.permission_type_id == pm_type_path) &
                                                      (Permission.root_app_name == app['cr_app_name'])). \
                                               with_entities(Permission.name).statement, rows=True)
    perm_from_db = set([perm[0] for perm in perm_from_db])
    diff = resources.difference(perm_from_db)
    if len(diff) > 0:
        await Permission.insert([{'id': None, 'name': perm, 'permission_type_id': pm_type_path,
                                  'root_app_name': app['cr_app_name']} for perm in diff])


def get_perm_entry(cr_app, item):
    reg_exp = r'(%s)' % cr_app['cr_app_prefix']
    return re.split(reg_exp, item, maxsplit=1).pop()
