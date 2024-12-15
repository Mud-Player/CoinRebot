from PySide6.QtCore import QObject, Signal, QDateTime

from BitgetAPI.BitgetRest import BitgetOrder


def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance

@singleton
class Database(QObject):
    buy_order_added = Signal(BitgetOrder)
    buy_order_removed = Signal(BitgetOrder)
    sell_order_added = Signal(BitgetOrder)
    sell_order_removed = Signal(BitgetOrder)

    def __init__(self):
        super().__init__()
        self.buy_orders = []
        self.sell_orders = []

    def push_buy_order(self, order: BitgetOrder):
        self.buy_orders.append(order)
        self.buy_order_added.emit(order)

    def push_sell_order(self, order: BitgetOrder):
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
