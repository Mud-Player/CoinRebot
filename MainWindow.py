from typing import Union

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt, QtMsgType, qInstallMessageHandler, QDateTime
from PySide6.QtWidgets import QGridLayout, QPushButton, QTextBrowser

import MiscSettings
from MiscSettings import BitgetConfiguration
from PlaceOrderEdit import PlaceOrderWidget
from OrderTable import OrderTableView
from TimeStatus import UTCTimeWidget

log_window: Union[QTextBrowser, None] = None
def qt_message_handler(mode, context, message):
    msg_type = {
        QtMsgType.QtDebugMsg: "DEBUG",
        QtMsgType.QtInfoMsg: "INFO",
        QtMsgType.QtWarningMsg: "WARNING",
        QtMsgType.QtCriticalMsg: "CRITICAL",
        QtMsgType.QtFatalMsg: "FATAL",
    }.get(mode, "UNKNOWN")

    formatted_message = f"[{msg_type} {QDateTime.currentDateTime().toString('hh:mm:ss')}] {message}"
    log_window.append(formatted_message)

class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        layout = QGridLayout(self)
        # utc
        time = UTCTimeWidget()
        layout.addWidget(time, 0, 0)
        # misc setup button
        misc_btn = QPushButton("Setup")
        layout.addWidget(misc_btn, 0, 1, Qt.AlignmentFlag.AlignRight)

        #
        # place order
        place_order = PlaceOrderWidget()
        layout.addWidget(place_order, 1, 0, 1, 1)

        # status view
        status_view = OrderTableView()
        layout.addWidget(status_view, 1, 1, 1, 1)

        # log
        log = QTextBrowser()
        layout.addWidget(log, 2, 0, 1, 2)

        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 1)

        # misc configuration
        self.misc = MiscSettings.MiscSettingWidget(self)

        config = BitgetConfiguration()
        if not config.apikey():
            self.misc.exec()
        misc_btn.clicked.connect(lambda : self.misc.exec())

        # message redirect to log
        global log_window
        log_window = log
        qInstallMessageHandler(qt_message_handler)
