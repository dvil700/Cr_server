from aiohttp import web
from . import views

routes = [web.get('/', views.index_handler, name='main'),
                    web.get('/users/', views.UserListView, name='users'),
                    web.view('/users/{ident}/', views.UserView, name='user'),
                    web.view('/users/new/', views.UserView, name='new_user'),
                    web.view('/users/change_pass/{ident}/', views.ChangePassView, name='change_pass'),
                    web.get('/permissions/', views.permissions_list, name='permissions'),
                    web.get('/groups/', views.GroupListView, name='groups'),
                    web.view('/groups/{ident}/', views.GroupView, name='group'),
                    web.view('/groups/new/', views.GroupView, name = 'new_group'),
                    web.get('/login/', views.login_handler, name='login'),
                    web.post('/login/', views.login_handler, name='login'),
                    web.get('/logout/', views.logout_handler, name='logout' ),
                    web.get('/fiscal_documents/', views.FiscalDocumentsListView, name ='fiscal_document_list'),
                    web.get('/operations/', views.OperationsListView, name ='operations_list')]