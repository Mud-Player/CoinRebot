from PySide6 import QtWidgets
from PySide6.QtCore import QDateTime, Slot, Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QLineEdit, QRadioButton, QDateTimeEdit, QPushButton, \
    QSizePolicy, QMessageBox, QComboBox

import Buttons
from BitgetAPI.BitgetRest import BitgetOrder, BitgetCommon
from GateAPI.GateRest import GateOrder, GateCommon
from MEXCAPI.MexcRest import MexcCommon, MexcOrder
from OrdersDB import Database
from RestClient import RestOrderBase, SymbolInfo


class PlaceOrderWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        layout = QGridLayout(self)

        self.order_toggle = Buttons.ToggleButtons('买入', '卖出')
        layout.addWidget(self.order_toggle, 0, 0, 1, 3)

        layout.addWidget(QLabel('交易所'), 1, 0)
        self.exchanges = QComboBox()
        self.exchanges.addItems(['Bitget', 'Gate.io', 'MEXC'])
        layout.addWidget(self.exchanges, 1, 1)
        self.exchanges.currentIndexChanged.connect(self._on_exchange_changed)
        self.exchange_remark = QLabel('交易对格式：BTCUSDT')
        layout.addWidget(self.exchange_remark, 1, 2)

        layout.addWidget(QLabel("交易对:"), 2, 0)
        self.symbol = QLineEdit()
        layout.addWidget(self.symbol, 2, 1)
        self.symbol_remark = QLabel()
        layout.addWidget(self.symbol_remark, 2, 2)
        self.symbol.editingFinished.connect(self._on_symbol_edit_finished)

        layout.addWidget(QLabel('价格:'), 3, 0)
        self.price = QLineEdit()
        layout.addWidget(self.price, 3, 1)
        self.price_remark = QLabel()
        layout.addWidget(self.price_remark, 3, 2)

        layout.addWidget(QLabel('数量:'), 4, 0)
        self.quantity = QLineEdit()
        layout.addWidget(self.quantity, 4, 1)
        self.quantity_remark = QLabel()
        layout.addWidget(self.quantity_remark, 4, 2)

        layout.addWidget(QLabel('频率:'), 5, 0)
        self.hz = QLineEdit()
        layout.addWidget(self.hz, 5, 1)

        self.timer_switch = QRadioButton('定时下单')
        layout.addWidget(self.timer_switch, 6, 0)
        self.timer_switch.toggled.connect(self._on_timer_switch_toggled)

        layout.addWidget(QLabel('定时时间:'), 7, 0)
        self.datetime = QDateTimeEdit()
        self.datetime.setDisplayFormat("yyyy.MM.dd hh:mm:ss")
        cur_time = QDateTime.currentDateTime()
        self.datetime.setDateTime(cur_time.addMSecs(-cur_time.time().msec()))
        layout.addWidget(self.datetime, 7, 1)

        self.apply = QPushButton('添加任务')
        self.apply.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.apply, 8, 0, 1, 3, Qt.AlignmentFlag.AlignHCenter)
        self.apply.clicked.connect(self._on_apply_or_cancel_clicked)
        self.apply.setProperty("started", False)

        self.timer_switch.toggle()

        self.database = Database()

        self.rest_client = None
        self._setup_new_client()

    def _setup_new_client(self):
        if self.rest_client:
            self.rest_client.deleteLater()
        match self.exchanges.currentIndex():
            case 0:
                self.rest_client = BitgetCommon()
            case 1:
                self.rest_client = GateCommon()
            case 2:
                self.rest_client = MexcCommon()
        self.rest_client.symbol_info_updated.connect(self._on_symbol_info_updated)
        self.rest_client.symbol_info_not_existed.connect(self._on_symbol_info_not_existed)

    def _on_exchange_changed(self):
        match self.exchanges.currentIndex():
            case 0:
                self.exchange_remark.setText('交易对格式: BTCUSDT')
            case 1:
                self.exchange_remark.setText('交易对格式: BTC_USDT')
            case 2:
                self.exchange_remark.setText('交易对格式: BTCUSDT')
        self._setup_new_client()
        if self.symbol.text():
            self.symbol.editingFinished.emit()

    def _on_timer_switch_toggled(self):
        if self.timer_switch.isChecked():
            self.datetime.setEnabled(True)
            self.apply.setText('添加任务')
        else:
            self.datetime.setEnabled(False)
            self.apply.setText('立即执行')

    def _on_symbol_edit_finished(self):
        self.rest_client.request_symbol(self.symbol.text())
        self.symbol_remark.setText('')
        self.price_remark.setText('')
        self.quantity_remark.setText('')

    def _on_symbol_info_not_existed(self):
        self.symbol_remark.setText('该交易对不存在')

    @Slot(SymbolInfo)
    def _on_symbol_info_updated(self, info:SymbolInfo):
        price_precision = info.price_precision
        quantity_precision = info.quantity_precision
        status = info.status
        self.symbol_remark.setText(f'上架状态：{status}')
        self.price_remark.setText(f'价格精度：{price_precision}')
        self.quantity_remark.setText(f'数量精度：{quantity_precision}')

    def _on_apply_or_cancel_clicked(self):
        # scheduled order
        if self.timer_switch.isChecked():
            self._place_order()
        else: # immediately order
            # start
            if not self.apply.property('started'):
                self._place_immediately_order()
                self.apply.setText('停止')
                self.timer_switch.setEnabled(False)
                self.apply.setProperty('started', True)
            else: # stop
                self._cancel_immediately_order()
                self.apply.setText('立即执行')
                self.timer_switch.setEnabled(True)
                self.apply.setProperty('started', False)

    def _place_immediately_order(self):
        self._place_order(True)
    
    def _cancel_immediately_order(self):
        if self.order_toggle.button1_isChecked():
            self.database.pop_buy_order().deleteLater()
        else:
            self.database.pop_sell_order().deleteLater()
    
    def _place_order(self, immediately = False):
        symbol = self.symbol.text()
        price = self.price.text()
        quantity = self.quantity.text()
        hz = int(self.hz.text())
        interval = 1000 / hz
        is_buy_order = self.order_toggle.button1_isChecked()
        order_type = RestOrderBase.OrderType.Buy if is_buy_order else RestOrderBase.OrderType.Sell
        order_cls = [BitgetOrder, GateOrder, MexcOrder]
        exchange_idx = self.exchanges.currentIndex()
        if immediately:
            order = order_cls[exchange_idx](order_type, symbol, price, quantity, interval)
        else:
            order = order_cls[exchange_idx](order_type, symbol, price, quantity, interval,self.datetime.dateTime().toMSecsSinceEpoch())

        result = order.place_order()
        if not result[0]:
            QMessageBox.warning(self, '添加任务失败', f'下单失败, 请检查下单参数: {result[1]}',
                                QMessageBox.StandardButton.Ok, QMessageBox.StandardButton.NoButton)
            return

        if is_buy_order:
            self.database.push_buy_order(order)
        else:
            self.database.push_sell_order(order)


