from .models import User


async def auth(login, passwd):
    user = User()
    await user.get_user(login, passwd)
    return user
