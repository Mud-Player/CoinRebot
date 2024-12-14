from PySide6 import QtWidgets
from PySide6.QtCore import Slot, QTime, QTimer, Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QMenu

import OrdersDB


def resize_header_to_contents(table: QTableWidget):
    table.resizeColumnsToContents()
    # 保存每一列的内容宽度
    column_widths = [table.columnWidth(col) for col in range(table.columnCount())]
    total_content_width = sum(column_widths)

    # 获取表格的总宽度
    total_table_width = table.viewport().width()

    # 计算剩余空间
    remaining_space = total_table_width - total_content_width

    if remaining_space > 0:
        # 计算每列应增加的宽度，按比例分配
        for col in range(table.columnCount()):
            additional_width = remaining_space * (column_widths[col] / total_content_width)
            new_width = column_widths[col] + additional_width
            table.setColumnWidth(col, int(new_width))


class OrderTableView(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.buy_orders = []
        self.sell_orders = []

        layout = QVBoxLayout(self)
        headers = ['交易对', '价格', '数量', '定时', '倒计时', '状态', '结果']

        layout.addWidget(QLabel('买入任务：'))
        self.buy_table = QTableWidget()
        layout.addWidget(self.buy_table)
        self.buy_table.setColumnCount(7)
        self.buy_table.setHorizontalHeaderLabels(headers)

        layout.addWidget(QLabel('卖出任务：'))
        self.sell_table = QTableWidget()
        layout.addWidget(self.sell_table)
        self.sell_table.setColumnCount(7)
        self.sell_table.setHorizontalHeaderLabels(headers)

        self.buy_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.buy_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.buy_table.customContextMenuRequested.connect(lambda pos: self._custom_context_requested(self.buy_table, pos))
        self.sell_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sell_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sell_table.customContextMenuRequested.connect(lambda pos: self._custom_context_requested(self.sell_table, pos))

        self.db = OrdersDB.Database()
        self.db.buy_order_added.connect(self._on_buy_order_added)
        self.db.sell_order_added.connect(self._on_sell_order_added)
        self.db.buy_order_removed.connect(self._on_buy_order_removed)
        self.db.sell_order_removed.connect(self._on_sell_order_removed)

        timer = QTimer(self)
        timer.setInterval(1000)
        timer.timeout.connect(self._update_all_order_item)
        timer.start()

    @Slot(OrdersDB.PlaceOrder)
    def _on_buy_order_added(self, order: OrdersDB.PlaceOrder):
        self._on_order_added(self.buy_table, order)

    @Slot(OrdersDB.PlaceOrder)
    def _on_sell_order_added(self, order: OrdersDB.PlaceOrder):
        self._on_order_added(self.sell_table, order)

    @Slot(OrdersDB.PlaceOrder)
    def _on_buy_order_removed(self, order: OrdersDB.PlaceOrder):
        self._on_order_removed_by_idx(self.buy_table, self.buy_orders.index(order))

    @Slot(OrdersDB.PlaceOrder)
    def _on_sell_order_removed(self, order: OrdersDB.PlaceOrder):
        self._on_order_removed_by_idx(self.sell_table, self.sell_orders.index(order))

    def _on_order_added(self, table, order):
        symbol = QTableWidgetItem(order.symbol)
        price = QTableWidgetItem(order.price)
        quantity = QTableWidgetItem(order.quantity)
        time = QTableWidgetItem(order.trigger_datetime.toString("yyyy.MM.dd hh:mm:ss"))
        countdown = QTableWidgetItem()
        status = QTableWidgetItem()
        result = QTableWidgetItem()
        idx = table.rowCount()

        table.insertRow(idx)
        for col, item in enumerate([symbol, price, quantity, time, countdown, status, result]):
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(idx, col, item)

        orders = self.buy_orders if table == self.buy_table else self.sell_orders
        orders.append(order)
        self._update_order_item_by_idx(table, orders.index(order))

        resize_header_to_contents(table)

    def _update_all_order_item(self):
        for idx in range(len(self.buy_orders)):
            self._update_order_item_by_idx(self.buy_table, idx)
        for idx in range(len(self.sell_orders)):
            self._update_order_item_by_idx(self.sell_table, idx)

    def _update_order_item_by_idx(self, table, idx: int):
        orders = self.buy_orders if table == self.buy_table else self.sell_orders
        order = orders[idx]
        countdown = table.item(idx, 4)
        countdown_ms = max(order.countdown_ms(), 0)
        count_down_str = QTime.fromMSecsSinceStartOfDay(countdown_ms).toString('hh:mm:ss')
        countdown.setText(count_down_str)

        status = table.item(idx, 5)
        if order.is_finished():
            status.setText('完成')
        elif order.is_running():
            status.setText('执行中')
        elif order.is_started():
            status.setText('等待')
        else:
            status.setText('unknown')

        result = table.item(idx, 6)
        succeed = order.succeed_count
        failed = order.failed_count
        total = succeed + failed
        if total == 0:
            result.setText('-')
        else:
            result.setText(f'{succeed}/{total}')

    def _custom_context_requested(self, table, pos):
        item = table.itemAt(pos)
        if item is None:
            return
        menu = QMenu()
        action = menu.addAction('删除')
        selected_action = menu.exec(table.viewport().mapToGlobal(pos))
        if selected_action == action:
            idx = item.row()
            if table == self.buy_table:
                self.db.remove_buy_order(idx).deleteLater()
            else:
                self.db.remove_sell_order(idx).deleteLater()

    def _on_order_removed_by_idx(self, table, idx:int):
        orders = self.buy_orders if table == self.buy_table else self.sell_orders
        orders.pop(idx)
        table.removeRow(idx)

