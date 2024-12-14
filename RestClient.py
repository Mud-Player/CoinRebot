from PySide6.QtCore import QObject, QJsonDocument, QDateTime, Qt, Signal, Slot, QTimer, qWarning, qDebug
from PySide6.QtNetwork import QNetworkReply, QNetworkAccessManager, QNetworkRequest

import utils
from MiscSettings import Configurations
from utils import get_timestamp
import  json

# Base Url
API_URL = 'https://api.bitget.com'
CONTRACT_WS_URL = 'wss://ws.bitget.com/mix/v1/stream'
SERVER_TIMESTAMP_URL = '/api/v2/public/time'
# http header
CONTENT_TYPE = 'Content-Type'
OK_ACCESS_KEY = 'ACCESS-KEY'
OK_ACCESS_SIGN = 'ACCESS-SIGN'
OK_ACCESS_TIMESTAMP = 'ACCESS-TIMESTAMP'
OK_ACCESS_PASSPHRASE = 'ACCESS-PASSPHRASE'
APPLICATION_JSON = 'application/json'

# header key
LOCALE = 'locale'

# method
GET = "GET"
POST = "POST"
DELETE = "DELETE"

# sign type
RSA = "RSA"
SHA256 = "SHA256"
SIGN_TYPE = SHA256

class RestClient(QObject):
    delay_ms = 0
    server_time_updated = Signal()
    server_timestamp_base = 0
    local_timestamp_base = 0

    def __init__(self, api_key=None, secret_key=None, passphrase=None):
        super().__init__()
        self.API_KEY = api_key if api_key is not None else Configurations.apikey()
        self.SECRET_KEY = secret_key if secret_key is not None else Configurations.secretkey()
        self.PASSPHRASE = passphrase if passphrase is not None else Configurations.passphrase()
        self.http_manager = QNetworkAccessManager()

    @property
    def rectified_timestamp(self):
        timestamp = self.server_timestamp_base + (get_timestamp() - self.local_timestamp_base)
        return timestamp

    def request(self, api_path, params, minimum_timestamp = None):
        url = API_URL + api_path

        timestamp = self.rectified_timestamp
        if minimum_timestamp is not None:
            timestamp = max(timestamp, minimum_timestamp)

        # sign & header
        body = json.dumps(params)
        sign = utils.sign(utils.pre_hash(timestamp, 'POST', api_path, str(body)), self.SECRET_KEY)
        if SIGN_TYPE == RSA:
            sign = utils.signByRSA(utils.pre_hash(timestamp, 'POST', api_path, str(body)), self.SECRET_KEY)
        headers = utils.get_header(self.API_KEY, sign, timestamp, self.PASSPHRASE)

        request = QNetworkRequest(url)
        for key, value in headers.items():
            request.setRawHeader(key.encode(), value.encode())  # `encode()` 将字符串转换为字节
        reply = self.http_manager.post(request, body.encode())
        return reply


    def request_utctime(self):
        request = QNetworkRequest(API_URL + SERVER_TIMESTAMP_URL)
        begin_ms = get_timestamp()
        reply = self.http_manager.get(request)
        reply.finished.connect(lambda : self._on_utc_replied(reply, begin_ms))

    def _on_utc_replied(self, reply: QNetworkReply, begin_ms):
        end_ms = get_timestamp()
        delta_ms = (end_ms - begin_ms) // 2
        self.local_timestamp_base = end_ms

        # predict delay
        delay = int(0.4 * self.delay_ms + 0.6 * delta_ms)
        self.delay_ms = delay

        data = reply.readAll().data()
        json_data = json.loads(data.decode('utf-8'))
        utc = int(json_data['data']['serverTime'])
        self.server_timestamp_base = utc + self.delay_ms
        reply.deleteLater()

        self.server_time_updated.emit()

class PlaceOrder(RestClient):
    succeed = Signal()
    failed = Signal()

    def __init__(self, symbol:str, price:str, quantity:str, interval = 1, trigger_datetime:QDateTime = QDateTime(),
                 api_key=None, secret_key=None, passphrase=None):
        super().__init__(api_key, secret_key, passphrase)
        self.orders = list()
        self.params = None
        self.symbol = symbol
        self.price = price
        self.quantity = quantity
        self.interval = interval
        self.trigger_datetime = trigger_datetime

        self.succeed_count = 0
        self.failed_count = 0
        self.error_codes = []

        self.request_timer = QTimer(self)
        self.request_timer.setInterval(interval)
        self.request_timer.timeout.connect(self._on_request_order)
        self.observe_timer = QTimer(self)   # in case of system time drifting
        self.observe_timer.timeout.connect(self._on_check_time)
        self.observe_timer.setSingleShot(True)

    def place_order(self):
        if self.params is not None:
            raise Exception('Do not place order over than two times with one instance.')
        params = dict()
        params['symbol'] = self.symbol
        params['side'] = 'buy'
        params['orderType'] = 'limit'
        params['force'] = 'gtc'
        params['price'] = self.price
        params['size'] = self.quantity
        self.params = params

        if self.trigger_datetime.isValid():
            delta_ms = self.trigger_datetime.toMSecsSinceEpoch() - self.rectified_timestamp
            if delta_ms < 0:
                qWarning(f'Error timer: {self.trigger_datetime.toString()}')
                return False
            self._on_check_time()
        else:   # start immediately
            self.trigger_datetime=QDateTime.currentDateTime()
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
            self.orders.append(int(order_id))
            self.succeed_count += 1
            self.request_timer.stop()
            self.succeed.emit()
            qDebug(f'下单成功: {str(self.params)}，累计成功下单{self.succeed_count}次')
        else:   # error
            self.failed_count += 1
            self.failed.emit()
            self.error_codes.append(int(code))
            qDebug(json_data)
