import json
from enum import Enum

from PySide6.QtCore import QObject, Slot, qDebug, Signal, QDateTime, QTimer, qWarning
from PySide6.QtNetwork import QNetworkReply

from RestClient import RestClient


class PlaceOrder(RestClient):
    succeed = Signal()
    failed = Signal()
    class OrderType(Enum):
        Buy = 1
        Sell = 2

    def __init__(self, order_type, symbol:str, price:str, quantity:str, interval = 1, trigger_datetime:QDateTime = QDateTime(),
                 api_key=None, secret_key=None, passphrase=None):
        super().__init__(api_key, secret_key, passphrase)
        self.order_type = order_type
        self.order_records = list()
        self.params = None
        self.symbol = symbol
        self.price = price
        self.quantity = quantity
        self.interval = interval
        self.trigger_datetime = trigger_datetime

        self.succeed_count = 0
        self.failed_count = 0
        self.error_messages = []

        self.request_timer = QTimer(self)
        self.request_timer.setInterval(interval)
        self.request_timer.timeout.connect(self._on_request_order)
        self.observe_timer = QTimer(self)   # in case of system time drifting
        self.observe_timer.timeout.connect(self._on_check_time)
        self.observe_timer.setSingleShot(True)

    def start(self):
        if self.params is not None:
            raise Exception('Do not place order over than two times with one instance.')
        params = dict()
        params['symbol'] = self.symbol
        params['side'] = 'buy' if self.order_type == PlaceOrder.OrderType.Buy else 'sell'
        params['orderType'] = 'limit'
        params['force'] = 'gtc'
        params['price'] = self.price
        params['size'] = self.quantity
        self.params = params

        if self.trigger_datetime.isValid():
            delta_ms = self.trigger_datetime.toMSecsSinceEpoch() - self.rectified_timestamp
            if delta_ms < 0:
                qWarning(f'定时时间 {self.trigger_datetime.toString()} 早于当前时间')
                return False
            self._on_check_time()
        else:   # start immediately
            self.trigger_datetime = QDateTime.fromMSecsSinceEpoch(self.rectified_timestamp)
            self._on_request_order()
            self.request_timer.start()
        return True


    def stop(self):
        self.request_timer.stop()
        self.observe_timer.stop()

    def is_started(self):
        return self.params is not None

    def is_running(self):
        return self.request_timer.isActive()

    def is_finished(self):
        return (self.failed_count + self.succeed_count) > 0 and not self.request_timer.isActive()

    def countdown_ms(self):
        delta_ms = self.trigger_datetime.toMSecsSinceEpoch() - self.rectified_timestamp - self.delay_ms
        return delta_ms

    def _on_check_time(self):
        delta_ms = self.countdown_ms()

        if delta_ms < 1000:    # trigger
            self._on_request_order()
            self.request_timer.start()
            qDebug(f'开始执行下单: {str(self.params)}')
        elif delta_ms < 300_000:   # 5min
            self.observe_timer.setInterval(delta_ms)
            self.observe_timer.start()
        else:   # > 5min
            check_time = delta_ms / 3 * 2
            self.observe_timer.setInterval(check_time)
            self.observe_timer.start()


    def _on_request_order(self):
        minimum_timestamp = self.trigger_datetime.toMSecsSinceEpoch()
        reply = self.request('/api/v2/spot/trade/place-order', self.params, minimum_timestamp)
        reply.finished.connect(lambda: self._on_replied(reply))

    @Slot(QNetworkReply)
    def _on_replied(self, reply):
        data = reply.readAll().data()
        json_data = json.loads(data)
        code = json_data['code']
        if code == '00000':    # success
            order_id = json_data['data']['orderId']
            self.order_records.append(int(order_id))
            self.succeed_count += 1
            self.request_timer.stop()
            self.succeed.emit()
            qDebug(f'下单成功: {str(self.params)}，累计成功下单{self.succeed_count}次')
        else:   # error
            self.failed_count += 1
            self.failed.emit()
            self.error_messages.append(json_data['msg'])
            qDebug(str(json_data))


def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance

class BuyOrder(PlaceOrder):
    def __init__(self, symbol:str, price:str, quantity:str, interval = 1, trigger_datetime:QDateTime = QDateTime(),
                 api_key=None, secret_key=None, passphrase=None):
        super().__init__(PlaceOrder.OrderType.Buy, symbol, price, quantity, interval, trigger_datetime,
                         api_key, secret_key, passphrase)


class SellOrder(PlaceOrder):
    def __init__(self, symbol: str, price: str, quantity: str, interval=1,
                 trigger_datetime: QDateTime = QDateTime(),
                 api_key=None, secret_key=None, passphrase=None):
        super().__init__(PlaceOrder.OrderType.Sell, symbol, price, quantity, interval, trigger_datetime,
                         api_key, secret_key, passphrase)


@singleton
class Database(QObject):
    buy_order_added = Signal(PlaceOrder)
    buy_order_removed = Signal(PlaceOrder)
    sell_order_added = Signal(PlaceOrder)
    sell_order_removed = Signal(PlaceOrder)

    def __init__(self):
        super().__init__()
        self.buy_orders = []
        self.sell_orders = []

    def push_buy_order(self, order: PlaceOrder):
        self.buy_orders.append(order)
        self.buy_order_added.emit(order)

    def push_sell_order(self, order: PlaceOrder):
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
