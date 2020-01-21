from db.model import Base
from auth.auth import get_standart_password_check_strategy
from auth.models import User, Permission, Permission_type, Group, user_permission, user_group, group_permission
from commands.models import Operation, IncomeData, CrHardware, CashRegister, Ofd, Company, OnlineCR, FiscalDocument
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import DB_ENGINE, DB_CONFIG
import os
from dotenv import load_dotenv
from pathlib import Path

def create_supeuser(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    user = session.query(User).first()
    if user:
        return
    print('Creating a superuser')
    login = input('Login:')
    passwd = passwd_check()
    pass_strategy = get_standart_password_check_strategy()
    passwd = pass_strategy.password_encode(passwd)
    super_user = User(login=login, passwd=passwd, enabled=True, superuser=True)
    session.add(super_user)
    session.commit()


def passwd_check():
    passwd = input('Password:')
    repeat = input('Repeat the password:')
    if passwd != repeat:
        print('Try again')
        return passwd_check()
    return passwd


def create_tables(engine):
    Base.metadata.create_all(engine)


if __name__ == '__main__':
    # загружаем переменные окружения
    env_path = Path('.') / 'settings.env'
    if not os.path.exists(env_path):
        raise FileExistsError('Не найден файл конфигурации settings.env')
    load_dotenv(dotenv_path=env_path)
    engine = create_engine('{engine}://{user}:{password}@{host}:{port}/{db}'.format(engine = DB_ENGINE, **DB_CONFIG))
    create_tables(engine)
    create_supeuser(engine)