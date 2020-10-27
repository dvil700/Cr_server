from .base import ShiftInformation, AbstractRegistratorDriverAdapter

import os


def get_available_adapters():
    dir_iterator = os.scandir(os.path.dirname(__file__))
    result = [item.name for item in dir_iterator if item.is_dir() and item.name[0] != '_']
    return result if len(result) else None