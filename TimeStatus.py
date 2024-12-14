from PySide6 import QtWidgets
from PySide6.QtCore import QTimer, Slot, QDateTime
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt

from RestClient import RestClient


class UTCTimeWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.addWidget(QLabel("时间"))
        self.time = QLabel("hh-mm-ss")
        layout.addWidget(self.time)
        layout.addItem(QSpacerItem(20, 20))
        layout.addWidget(QLabel("延迟"))
        self.delay = QLabel("0ms")
        layout.addWidget(self.delay)

        layout.addItem(QSpacerItem(20, 20, hData=QSizePolicy.Policy.Expanding))

        self.time_client = RestClient()
        self.time_client.server_time_updated.connect(self.on_utc_updated)
        timer = QTimer(self)
        timer.timeout.connect(self.time_client.request_utctime)
        timer.setInterval(1000)
        timer.start()

    @Slot()
    def on_utc_updated(self):
        self.time.setText(QDateTime.fromMSecsSinceEpoch(self.time_client.rectified_timestamp).toString())
        self.delay.setText(str(self.time_client.delay_ms) + 'ms')
