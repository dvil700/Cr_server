from aiohttp import web
from commands.views import command_handler, result_handler
from .commands import COMMANDS_ALLOWED


def make_command_routes():
    result = [web.get('/get_result', result_handler), ]
    for command_name in COMMANDS_ALLOWED.keys():
        result.append(web.post('/%s.do'%command_name.lower(), command_handler))
    return result