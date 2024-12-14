import json

from PySide6.QtCore import QObject, QDateTime, Signal, Slot, QTimer, qWarning, qDebug
from PySide6.QtNetwork import QNetworkReply, QNetworkAccessManager, QNetworkRequest

import consts as c
import utils
from MiscSettings import Configurations
from utils import get_timestamp


class RestClient(QObject):
    delay_ms = 0
    server_time_updated = Signal()
    symbol_info_updated = Signal(dict)
    symbol_info_not_existed = Signal()

    server_timestamp_base = 0
    local_timestamp_base = 0

    def __init__(self, api_key=None, secret_key=None, passphrase=None):
        super().__init__()
        self.API_KEY = api_key if api_key is not None else Configurations.apikey()
        self.SECRET_KEY = secret_key if secret_key is not None else Configurations.secretkey()
        self.PASSPHRASE = passphrase if passphrase is not None else Configurations.passphrase()
        self.http_manager = QNetworkAccessManager(self)

    @property
    def rectified_timestamp(self):
        timestamp = self.server_timestamp_base + (get_timestamp() - self.local_timestamp_base)
        return timestamp

    def request(self, api_path, params, minimum_timestamp = None):
        url = c.API_URL + api_path

        timestamp = self.rectified_timestamp
        if minimum_timestamp is not None:
            timestamp = max(timestamp, minimum_timestamp)

        # sign & header
        body = json.dumps(params)
        sign = utils.sign(utils.pre_hash(timestamp, 'POST', api_path, str(body)), self.SECRET_KEY)
        if c.SIGN_TYPE == c.RSA:
            sign = utils.signByRSA(utils.pre_hash(timestamp, 'POST', api_path, str(body)), self.SECRET_KEY)
        headers = utils.get_header(self.API_KEY, sign, timestamp, self.PASSPHRASE)

        request = QNetworkRequest(url)
        for key, value in headers.items():
            request.setRawHeader(key.encode(), value.encode())  # `encode()` 将字符串转换为字节
        reply = self.http_manager.post(request, body.encode())
        return reply

    def request_utctime(self):
        request = QNetworkRequest(c.API_URL + c.SERVER_TIMESTAMP_URL)
        begin_ms = get_timestamp()
        reply = self.http_manager.get(request)
        reply.finished.connect(lambda : self._on_utc_replied(reply, begin_ms))

    def request_symbol(self, symbol):
        url = c.API_URL + c.SYMBOL_INFO_URL + f'?symbol={symbol}'
        request = QNetworkRequest(url)
        reply = self.http_manager.get(request)
        reply.finished.connect(lambda : self._on_symbol_info_replied(reply))

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

    def _on_symbol_info_replied(self, reply: QNetworkReply):
        data = reply.readAll().data()
        json_data = json.loads(data.decode('utf-8'))
        code = json_data['code']
        if code != '00000':
            if code == '40034':
                self.symbol_info_not_existed.emit()
            return
        info = json_data['data'][0]
        self.symbol_info_updated.emit(info)
