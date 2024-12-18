import json

from PySide6.QtCore import qDebug, Slot
from PySide6.QtNetwork import QNetworkRequest, QNetworkReply, QNetworkAccessManager

from GateAPI.utils_gate import gen_signed_header
from MiscSettings import GateConfiguration
from RestClient import RestBase, SymbolInfo, RestOrderBase
from utils import get_timestamp, setup_header
import GateAPI.consts_gate as const

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
        try:
            json_data = json.loads(data.decode('utf-8'))
        except:
            return
        utc = json_data['server_time']
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
                 api_key=None, secret_key=None):
        super().__init__(order_type, symbol, price, quantity, interval, trigger_timestamp)
        self.exchange = 'Gate.io'

        config = GateConfiguration()
        self.API_KEY = api_key if api_key is not None else config.apikey()
        self.SECRET_KEY = secret_key if secret_key is not None else config.secretkey()
        params = dict()
        params['currency_pair'] = self.symbol
        params['side'] = 'buy' if self.order_type == RestOrderBase.OrderType.Buy else 'sell'
        params['orderType'] = 'limit'
        params['force'] = 'gtc'
        params['price'] = self.price
        params['amount'] = self.quantity
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
        super().order_trigger_start_event()
        qDebug(f'开始执行下单: {str(self.params)}')

    def order_trigger_event(self):
        minimum_timestamp = self.trigger_timestamp
        reply = self._request('/api/v4/spot/orders', self.params, minimum_timestamp)
        reply.finished.connect(lambda: self._on_replied(reply))

    def cancel_order(self):
        pass

    def _request(self, api_path, params, minimum_timestamp=None):
        url = const.API_URL + api_path

        timestamp = self.rectified_timestamp
        if minimum_timestamp is not None:
            timestamp = max(timestamp, minimum_timestamp)

        # sign & header
        body = json.dumps(params)
        sign_headers = gen_signed_header(self.API_KEY, self.SECRET_KEY, int(timestamp / 1000), 'POST', api_path, None, body)
        headers = const.HEADERS
        headers.update(sign_headers)

        request = QNetworkRequest(url)
        setup_header(headers, request)
        reply = self.http_manager.post(request, body.encode())
        return reply

    @Slot(QNetworkReply)
    def _on_replied(self, reply):
        status_code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        data = reply.readAll().data()
        json_data = json.loads(data)
        if status_code == 200 or status_code == 201:
            order_id = json_data['id']
            self.order_records.append(int(order_id))
            self.succeed_count += 1
            self.error_code = status_code
            self.stop_order_trigger()
            if self.succeed_count == 1:
                qDebug(f'挂单成功，结束任务：{str(self.params)}')
            self.succeed.emit()
        else:
            err_label = json_data['label']
            self.error_code = 1
            match err_label:
                case 'INVALID_CURRENCY_PAIR' | 'BALANCE_NOT_ENOUGH':
                    self.stop_order_trigger()
                    qDebug(f'挂单失败: {json_data}')
                    self.failed.emit()
                case _:
                    if not self.is_finished():
                        qDebug(str(json_data))

            self.failed_count += 1
