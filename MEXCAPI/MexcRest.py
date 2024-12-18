import json

from PySide6.QtCore import qDebug, Slot
from PySide6.QtNetwork import QNetworkRequest, QNetworkReply, QNetworkAccessManager

from MEXCAPI.utils_mexc import gen_signed_body
from MiscSettings import MexcConfiguration
from RestClient import RestBase, SymbolInfo, RestOrderBase
from utils import get_timestamp, setup_header
import MEXCAPI.consts_mexc as const

def error_msg(status_code):
    msg = {
        401: '身份认证、权限错误',
        403: '违反WAF限制(Web应用程序防火墙)',
        429: '警告访问频次超限，即将被封IP',
    }
    return msg[status_code] if status_code in msg else '未知错误'

class MexcCommon(RestBase):
    _delay_ms = 0
    server_timestamp_base = 0
    local_timestamp_base = 0

    def __init__(self):
        super().__init__()

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
        try:
            json_data = json.loads(data.decode('utf-8'))
        except:
            return
        utc = json_data['serverTime']
        self.server_timestamp_base = utc + self.delay_ms
        reply.deleteLater()

        self.server_time_updated.emit()

    def _on_symbol_info_replied(self, reply: QNetworkReply):
        status_code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        if status_code != 200:
            qDebug(f'获取交易对出错：{error_msg(status_code)}')
            self.symbol_info_not_existed.emit('symbol')
            return

        data = reply.readAll().data()
        json_data = json.loads(data.decode('utf-8'))
        json_data = json_data['symbols'][0]
        status = json_data['status']
        status_dict = {
            '1': '上架',
            '2': '暂停',
            '3': '下架'
        }
        info = SymbolInfo(json_data['symbol'], status_dict[status],
                          json_data['quotePrecision'], json_data['quoteAssetPrecision'])
        self.symbol_info_updated.emit(info)


class MexcOrder(RestOrderBase):
    common = MexcCommon()

    def __init__(self, order_type: RestOrderBase.OrderType, symbol: str, price: str, quantity: str, interval=1,
                 trigger_timestamp=-1,
                 api_key=None, secret_key=None):
        super().__init__(order_type, symbol, price, quantity, interval, trigger_timestamp)
        self.exchange = 'Mexc.io'

        config = MexcConfiguration()
        self.API_KEY = api_key if api_key is not None else config.apikey()
        self.SECRET_KEY = secret_key if secret_key is not None else config.secretkey()
        params = dict()
        params['symbol'] = self.symbol
        params['side'] = 'BUY' if self.order_type == RestOrderBase.OrderType.Buy else 'SELL'
        params['type'] = 'LIMIT'
        params['price'] = self.price
        params['quantity'] = self.quantity
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

    def order_trigger_5s_countdown_event(self):
        self._head('/api/v3/order', self.params)

    def order_trigger_start_event(self):
        super().order_trigger_start_event()
        qDebug(f'开始执行下单: {str(self.params)}')
        qDebug(f'{get_timestamp()}')

    def order_trigger_event(self):
        minimum_timestamp = self.trigger_timestamp
        reply = self._request('/api/v3/order', self.params, minimum_timestamp)
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
        params = params | {'timestamp': timestamp}
        body = gen_signed_body(self.SECRET_KEY, timestamp, params)
        headers = const.HEADERS.copy()
        headers['X-MEXC-APIKEY'] = self.API_KEY

        request = QNetworkRequest(url)
        setup_header(headers, request)
        reply = self.http_manager.post(request, body.encode())
        return reply

    def _head(self, api_path, params, minimum_timestamp=None):
        url = const.API_URL + api_path

        headers = const.HEADERS.copy()
        headers['X-MEXC-APIKEY'] = self.API_KEY

        request = QNetworkRequest(url)
        setup_header(headers, request)
        reply = self.http_manager.head(request)
        return reply

    @Slot(QNetworkReply)
    def _on_replied(self, reply):
        status_code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        data = reply.readAll().data()
        try:
            json_data = json.loads(data)
        except:
            return
        qDebug(f'reply {get_timestamp()}')
        if status_code == 200 or status_code == 201:
            order_id = json_data['orderId']
            self.order_records.append(order_id)
            self.succeed_count += 1
            self.stop_order_trigger()
            if self.succeed_count == 1:
                qDebug(f'挂单成功，结束任务：{str(self.params)}')
            self.succeed.emit()
        else:
            self.failed_count += 1
            self.failed.emit()
            if not self.is_finished():
                qDebug(str(json_data))

