from aiohttp import web
from commands.views import command_handler, result_handler

routes = [web.post('/proccess', command_handler), web.get('/get_result', result_handler),]