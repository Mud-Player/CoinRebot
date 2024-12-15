import json

from PySide6.QtCore import qDebug
from PySide6.QtNetwork import QNetworkRequest, QNetworkReply, QNetworkAccessManager

from RestClient import RestBase, SymbolInfo, RestOrderBase
from utils import get_timestamp
import GateAPI.consts_gate as const

def setup_header(headers, request: QNetworkRequest):
    for key, value in headers.items():
        request.setRawHeader(key.encode(), value.encode())  # `encode()` 将字符串转换为字节

def error_msg(status_code):
    msg = {
        202: '请求已被服务端接受，但是仍在处理中',
        204: '请求成功，服务端没有提供返回体',
        400: '无效请求',
        401: '认证失败',
        404: '未找到',
        429: '请求过于频繁'
    }
    return msg[status_code] if status_code in msg else '未知错误'

class GateCommon(RestBase):
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
        setup_header(const.HEADERS, request)
        begin_ms = get_timestamp()
        reply = self.http_manager.get(request)
        reply.finished.connect(lambda: self._on_utc_replied(reply, begin_ms))

    def request_symbol(self, symbol):
        url = const.API_URL + const.SYMBOL_INFO_URL + f'/{symbol}'
        request = QNetworkRequest(url)
        setup_header(const.HEADERS, request)
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
        utc = json_data['server_time']
        self.server_timestamp_base = utc + self.delay_ms
        reply.deleteLater()

        self.server_time_updated.emit()

    def _on_symbol_info_replied(self, reply: QNetworkReply):
        status_code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        if status_code != 200:
            qDebug(f'获取交易对出错：{error_msg(status_code)}')
            return

        data = reply.readAll().data()
        json_data = json.loads(data.decode('utf-8'))
        status = json_data['trade_status']
        status_dict = {
            'untradable': '无法交易',
            'buyable': '仅可买入',
            'sellable': '仅可卖出',
            'tradable': '可以交易'
        }
        info = SymbolInfo(json_data['id'], status_dict[status],
                          json_data['precision'], json_data['amount_precision'])
        self.symbol_info_updated.emit(info)


class GateOrder(RestOrderBase):
    common = GateCommon()

    def __init__(self, order_type: RestOrderBase.OrderType, symbol: str, price: str, quantity: str, interval=1,
                 trigger_timestamp=-1,
                 api_key=None, secret_key=None, passphrase=None):
        super().__init__(order_type, symbol, price, quantity, interval, trigger_timestamp)
        self.API_KEY = api_key if api_key is not None else Configurations.apikey()
        self.SECRET_KEY = secret_key if secret_key is not None else Configurations.secretkey()
        self.PASSPHRASE = passphrase if passphrase is not None else Configurations.passphrase()
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
        for key, value in headers.items():
            request.setRawHeader(key.encode(), value.encode())  # `encode()` 将字符串转换为字节
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
            self.succeed.emit()
        else:  # error
            self.failed_count += 1
            self.failed.emit()
            qDebug(str(json_data))