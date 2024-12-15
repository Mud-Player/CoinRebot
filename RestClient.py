from abc import abstractmethod, ABCMeta
from enum import Enum

from PySide6.QtCore import QObject, Signal, QTimer, QDateTime
from PySide6.QtNetwork import QNetworkAccessManager


class MetaQObjectABC(type(QObject), ABCMeta):
    pass

class RestBase(QObject, metaclass=MetaQObjectABC):
    server_time_updated = Signal()
    symbol_info_updated = Signal(dict)
    symbol_info_not_existed = Signal()
    
    def __init__(self):
        super().__init__()

    @property
    @abstractmethod
    def rectified_timestamp(self):
        pass
    
    @property
    @abstractmethod
    def delay_ms(self):
        pass

    @abstractmethod
    def request_utctime(self):
        pass

    @abstractmethod
    def request_symbol(self, symbol):
        pass
    

class RestOrderBase(RestBase):
    succeed = Signal()
    failed = Signal()

    class OrderType(Enum):
        Buy = 1
        Sell = 2

    def __init__(self, order_type:OrderType, symbol:str, price:str, quantity:str, interval = 1, trigger_timestamp=-1):
        super().__init__()
        self.order_type = order_type
        self.symbol = symbol
        self.price = price
        self.quantity = quantity
        self.interval = interval
        self.trigger_timestamp = trigger_timestamp
        self.order_records = []
        self.succeed_count = 0
        self.failed_count = 0

        self.http_manager = QNetworkAccessManager(self)

        self.trigger_timer = QTimer(self)
        self.trigger_timer.setInterval(interval)
        self.trigger_timer.timeout.connect(self.order_trigger_event)
        self.trigger_check_timer = QTimer(self)  # in case of system time drifting
        self.trigger_check_timer.timeout.connect(self._on_check_time)
        self.trigger_check_timer.setSingleShot(True)

    def place_order(self):
        server_time = self.rectified_timestamp
        if self.trigger_timestamp > 0:
            delta_ms = self.trigger_timestamp - server_time
            if delta_ms < 0:
                msg = (f'定时时间 {QDateTime.fromMSecsSinceEpoch(self.trigger_timestamp).toString()} '
                       f'不能晚于当前时间 {QDateTime.fromMSecsSinceEpoch(server_time).toString()}')
                return False, msg
            self._on_check_time()
        else:  # start immediately
            self.trigger_timestamp = server_time
            self.order_trigger_start_event()
        return True, 'success'

    @abstractmethod
    def cancel_order(self):
        pass

    def stop_order_trigger(self):
        self.trigger_timer.stop()

    def order_trigger_start_event(self):
        self.order_trigger_event()
        self.trigger_timer.start()

    @abstractmethod
    def order_trigger_event(self):
        pass

    @abstractmethod
    def is_running(self):
        pass

    def is_trigger_running(self):
        return self.trigger_timer.isActive()

    def countdown_ms(self):
        delta_ms = self.trigger_timestamp - self.rectified_timestamp - self.delay_ms
        return delta_ms

    def _on_check_time(self):
        delta_ms = self.countdown_ms()

        if delta_ms < 1000:    # trigger
            self.order_trigger_start_event()
        elif delta_ms < 300_000:   # 5min
            self.trigger_check_timer.setInterval(delta_ms)
            self.trigger_check_timer.start()
        else:   # > 5min
            check_time = delta_ms / 3 * 2
            self.trigger_check_timer.setInterval(check_time)
            self.trigger_check_timer.start()
