from PySide6 import QtWidgets
from PySide6.QtCore import QTimer, QDateTime
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSpacerItem, QSizePolicy

from BitgetAPI.BitgetRest import BitgetCommon
from GateAPI.GateRest import GateCommon
from MEXCAPI.MexcRest import MexcCommon


class UTCTimeWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        # Bitget
        layout.addWidget(QLabel("Bitget:"))
        self.bitget_time = QLabel("hh-mm-ss")
        layout.addWidget(self.bitget_time)
        self.bitget_delay = QLabel("0ms")
        layout.addWidget(self.bitget_delay)
        self.bitget_client = BitgetCommon()
        self.bitget_client.server_time_updated.connect(self._on_bitget_time_updated)

        layout.addItem(QSpacerItem(20, 20))

        # Gate
        layout.addWidget(QLabel("Gate:"))
        self.gate_time = QLabel("hh-mm-ss")
        layout.addWidget(self.gate_time)
        self.gate_delay = QLabel("0ms")
        layout.addWidget(self.gate_delay)
        self.gate_client = GateCommon()
        self.gate_client.server_time_updated.connect(self._on_gate_time_updated)

        layout.addItem(QSpacerItem(20, 20))

        # Mexc
        layout.addWidget(QLabel("Mexc:"))
        self.mexc_time = QLabel("hh-mm-ss")
        layout.addWidget(self.mexc_time)
        self.mexc_delay = QLabel("0ms")
        layout.addWidget(self.mexc_delay)
        self.mexc_client = MexcCommon()
        self.mexc_client.server_time_updated.connect(self._on_mexc_time_updated)

        layout.addItem(QSpacerItem(20, 20, hData=QSizePolicy.Policy.Expanding))
        
        timer = QTimer(self)
        timer.timeout.connect(lambda : [self.bitget_client.request_utctime(),
                                        self.gate_client.request_utctime(),
                                        self.mexc_client.request_utctime(),])
        timer.setInterval(1000)
        timer.start()

    def _on_bitget_time_updated(self):
        self.bitget_time.setText(QDateTime.fromMSecsSinceEpoch(self.bitget_client.rectified_timestamp).toString("yyyy.MM.dd hh:mm:ss"))
        self.bitget_delay.setText(str(self.bitget_client.delay_ms) + 'ms')


    def _on_gate_time_updated(self):
        self.gate_time.setText(QDateTime.fromMSecsSinceEpoch(self.gate_client.rectified_timestamp).toString("yyyy.MM.dd hh:mm:ss"))
        self.gate_delay.setText(str(self.gate_client.delay_ms) + 'ms')

    def _on_mexc_time_updated(self):
        self.mexc_time.setText(QDateTime.fromMSecsSinceEpoch(self.mexc_client.rectified_timestamp).toString("yyyy.MM.dd hh:mm:ss"))
        self.mexc_delay.setText(str(self.mexc_client.delay_ms) + 'ms')
