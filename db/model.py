from .db import Data_base


class Model:

    def __init__(self, db_object=None):
        if not db_object:
            db_object = Data_base()
        self.db = db_object
