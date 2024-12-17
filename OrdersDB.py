from PySide6.QtCore import QObject, Signal, QDateTime

from BitgetAPI.BitgetRest import BitgetOrder
from RestClient import RestOrderBase


def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance

@singleton
class Database(QObject):
    buy_order_added = Signal(RestOrderBase)
    buy_order_removed = Signal(RestOrderBase)
    sell_order_added = Signal(RestOrderBase)
    sell_order_removed = Signal(RestOrderBase)

    def __init__(self):
        super().__init__()
        self.buy_orders = []
        self.sell_orders = []

    def push_buy_order(self, order: RestOrderBase):
        self.buy_orders.append(order)
        self.buy_order_added.emit(order)

    def push_sell_order(self, order: RestOrderBase):
        self.sell_orders.append(order)
        self.sell_order_added.emit(order)

    def remove_buy_order(self, idx: int):
        order = self.buy_orders.pop(idx)
        self.buy_order_removed.emit(order)
        return order

    def remove_sell_order(self, idx: int):
        order = self.sell_orders.pop(idx)
        self.sell_order_removed.emit(order)
        return order

    def pop_buy_order(self):
        order = self.buy_orders.pop()
        self.buy_order_removed.emit(order)
        return order

    def pop_sell_order(self):
        order = self.sell_orders.pop()
        self.sell_order_removed.emit(order)
        return order

    def top_order(self):
        order = self.sell_orders.pop()
        self.sell_order_removed.emit(order)
