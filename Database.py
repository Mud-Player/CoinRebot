import queue

from PySide6.QtCore import QObject

from RestClient import PlaceOrder


def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance

@singleton
class Database(QObject):
    def __init__(self):
        super().__init__()
        self.list = []

    def push_order(self, order: PlaceOrder):
        self.list.append(order)

    def pop_order(self):
        pass

    def top_order(self):
        pass
