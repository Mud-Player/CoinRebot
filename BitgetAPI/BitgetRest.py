import json

from PySide6.QtCore import qDebug, Slot, QDateTime
from PySide6.QtNetwork import QNetworkRequest, QNetworkReply, QNetworkAccessManager

import BitgetAPI.consts_bitget as const
import BitgetAPI.utils_bitget as utils
from utils import get_timestamp, setup_header
from MiscSettings import BitgetConfiguration
from RestClient import RestOrderBase, RestBase, SymbolInfo


class BitgetCommon(RestBase):
    _delay_ms = 0
    server_timestamp_base = 0
    local_timestamp_base = 0

    def __init__(self):
        super().__init__()
        self.http_manager = QNetworkAccessManager(self)

    @property
    def rectified_timestamp(self):
        timestamp = self.server_timestamp_base + (get_timestamp() - self.local_timestamp_base)
        return timestamp

    @property
    def delay_ms(self):
        return self._delay_ms

    def request_utctime(self):
        request = QNetworkRequest(const.API_URL + const.SERVER_TIMESTAMP_URL)
        begin_ms = get_timestamp()
        reply = self.http_manager.get(request)
        reply.finished.connect(lambda: self._on_utc_replied(reply, begin_ms))

    def request_symbol(self, symbol):
        url = const.API_URL + const.SYMBOL_INFO_URL + f'?symbol={symbol}'
        request = QNetworkRequest(url)
        reply = self.http_manager.get(request)
        reply.finished.connect(lambda: self._on_symbol_info_replied(reply))

    def _on_utc_replied(self, reply: QNetworkReply, begin_ms):
        end_ms = get_timestamp()
        delta_ms = (end_ms - begin_ms) // 2
        self.local_timestamp_base = end_ms

        # predict delay
        delay = int(0.4 * self.delay_ms + 0.6 * delta_ms)
        self._delay_ms = delay

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
                symbol = json_data['msg'].split()[1] # "Parameter xxx does not exist"
                self.symbol_info_not_existed.emit(symbol)
            return

        symbol_data = json_data['data'][0]
        symbol = symbol_data['symbol']
        price_precision = symbol_data['pricePrecision']
        quantity_precision = symbol_data['quantityPrecision']
        status = symbol_data['status']
        status_dict = {
            'offline': '维护',
            'gray': '灰度',
            'online': '上线',
            'halt': '停盘'
        }
        info = SymbolInfo(symbol, status_dict[status], price_precision, quantity_precision)
        self.symbol_info_updated.emit(info)


class BitgetOrder(RestOrderBase):
    common = BitgetCommon()

    def __init__(self, order_type: RestOrderBase.OrderType, symbol: str, price: str, quantity: str, interval=1,
                 trigger_timestamp=-1,
                 api_key=None, secret_key=None, passphrase=None):
        super().__init__(order_type, symbol, price, quantity, interval, trigger_timestamp)
        self.exchange = 'Bitget'

        config = BitgetConfiguration()
        self.API_KEY = api_key if api_key is not None else config.apikey()
        self.SECRET_KEY = secret_key if secret_key is not None else config.secretkey()
        self.PASSPHRASE = passphrase if passphrase is not None else config.passphrase()
        params = dict()
        params['symbol'] = self.symbol
        params['side'] = 'buy' if self.order_type == RestOrderBase.OrderType.Buy else 'sell'
        params['orderType'] = 'limit'
        params['force'] = 'gtc'
        params['price'] = self.price
        params['size'] = self.quantity
        self.params = params

        self.common.server_time_updated.connect(self.server_time_updated.emit)
        self.common.symbol_info_updated.connect(self.symbol_info_updated.emit)
        self.common.symbol_info_not_existed.connect(self.symbol_info_not_existed.emit)

    @property
    def rectified_timestamp(self):
        return self.common.rectified_timestamp

    @property
    def delay_ms(self):
        return self.common.delay_ms

    def request_utctime(self):
        self.common.request_utctime()

    def request_symbol(self, symbol):
        self.common.request_symbol(symbol)

    def order_trigger_start_event(self):
        qDebug(f'开始执行下单: {str(self.params)}')
        super().order_trigger_start_event()

    def order_trigger_event(self):
        minimum_timestamp = self.trigger_timestamp
        reply = self._request('/api/v2/spot/trade/place-order', self.params, minimum_timestamp)
        reply.finished.connect(lambda: self._on_replied(reply))

    def cancel_order(self):
        pass

    def is_finished(self):
        return self.succeed_count > 0

    def is_running(self):
        return self.countdown_ms() <= 0 and self.is_trigger_running()

    def _request(self, api_path, params, minimum_timestamp=None):
        url = const.API_URL + api_path

        timestamp = self.rectified_timestamp
        if minimum_timestamp is not None:
            timestamp = max(timestamp, minimum_timestamp)

        # sign & header
        body = json.dumps(params)
        sign = utils.sign(utils.pre_hash(timestamp, 'POST', api_path, str(body)), self.SECRET_KEY)
        headers = utils.get_header(self.API_KEY, sign, timestamp, self.PASSPHRASE)

        request = QNetworkRequest(url)
        setup_header(headers, request)
        reply = self.http_manager.post(request, body.encode())
        return reply

    @Slot(QNetworkReply)
    def _on_replied(self, reply):
        data = reply.readAll().data()
        json_data = json.loads(data)
        code = json_data['code']
        if code == '00000':  # success
            order_id = json_data['data']['orderId']
            self.order_records.append(int(order_id))
            self.succeed_count += 1
            self.stop_order_trigger()
            if self.succeed_count == 1:
                qDebug(f'挂单成功，结束任务：{str(self.params)}')
            self.succeed.emit()
        else:  # error
            self.failed_count += 1
            self.failed.emit()
            if not self.is_finished():
                qDebug(str(json_data))
