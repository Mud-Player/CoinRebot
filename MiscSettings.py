from PySide6 import QtWidgets
from PySide6.QtCore import QSettings
from PySide6.QtNetwork import QNetworkProxy
from PySide6.QtWidgets import QLabel, QLineEdit, QSpacerItem, QRadioButton, QPushButton, QWidget, QGridLayout


class Configuration:
    settings = QSettings("Li.Player", "CoinRebot")

class ProxyConfiguration(Configuration):
    def __init__(self):
        super().__init__()

    def use_proxy(self):
        self.settings.beginGroup('Proxy')
        ret = bool(self.settings.value("use_proxy", False, type=bool))
        self.settings.endGroup()
        return ret

    def set_use_proxy(self, value):
        self.settings.beginGroup('Proxy')
        self.settings.setValue("use_proxy", value)
        self.settings.endGroup()

    def proxy_ip(self):
        self.settings.beginGroup('Proxy')
        ret = str(self.settings.value("proxy_ip", "127.0.0.1"))
        self.settings.endGroup()
        return ret

    def set_proxy_ip(self, value):
        self.settings.beginGroup('Proxy')
        self.settings.setValue("proxy_ip", value)
        self.settings.endGroup()

    def proxy_port(self) -> int:
        self.settings.beginGroup('Proxy')
        ret = self.settings.value("proxy_port", defaultValue=1080, type=int)
        self.settings.endGroup()
        return ret

    def set_proxy_port(self, value: int):
        self.settings.beginGroup('Proxy')
        self.settings.setValue("proxy_port", value)
        self.settings.endGroup()


class BitgetConfiguration(Configuration):

    def __init__(self):
        super().__init__()

    def __del__(self):
        self.settings.sync()

    def apikey(self):
        self.settings.beginGroup('Bitget')
        ret = str(self.settings.value("APIKey", ""))
        self.settings.endGroup()
        return ret

    def set_apikey(self, value):
        self.settings.beginGroup('Bitget')
        self.settings.setValue("APIKey", value)
        self.settings.endGroup()

    def secretkey(self):
        self.settings.beginGroup('Bitget')
        ret = str(self.settings.value("Secretkey", ""))
        self.settings.endGroup()
        return ret

    def set_secretkey(self, value):
        self.settings.beginGroup('Bitget')
        self.settings.setValue("Secretkey", value)
        self.settings.endGroup()

    def passphrase(self):
        self.settings.beginGroup('Bitget')
        ret = str(self.settings.value("Passphrase", ""))
        self.settings.endGroup()
        return ret

    def set_passphrase(self, value):
        self.settings.beginGroup('Bitget')
        self.settings.setValue("Passphrase", value)
        self.settings.endGroup()


class GateConfiguration(Configuration):

    def __init__(self):
        super().__init__()

    def __del__(self):
        self.settings.sync()

    def apikey(self):
        self.settings.beginGroup('Gate')
        ret = str(self.settings.value("APIKey", ""))
        self.settings.endGroup()
        return ret

    def set_apikey(self, value):
        self.settings.beginGroup('Gate')
        self.settings.setValue("APIKey", value)
        self.settings.endGroup()

    def secretkey(self):
        self.settings.beginGroup('Gate')
        ret = str(self.settings.value("Secretkey", ""))
        self.settings.endGroup()
        return ret

    def set_secretkey(self, value):
        self.settings.beginGroup('Gate')
        self.settings.setValue("Secretkey", value)
        self.settings.endGroup()

def _apply_proxy():
    proxy = ProxyConfiguration()
    if proxy.use_proxy():
        proxy = QNetworkProxy(QNetworkProxy.ProxyType.HttpProxy,
                              proxy.proxy_ip(), proxy.proxy_port())
        QNetworkProxy.setApplicationProxy(proxy)
    else:
        proxy = QNetworkProxy(QNetworkProxy.ProxyType.NoProxy)
        QNetworkProxy.setApplicationProxy(proxy)


class MiscSettingWidget(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)

        # Bitget
        layout.addWidget(QLabel('Bitget'))
        bitget = BitgetConfiguration()
        bitget_layout = QGridLayout()
        # api key
        bitget_layout.addWidget(QLabel("APIKey:"), 0, 0)
        api_key = QLineEdit(bitget.apikey())
        self.api_key = api_key
        bitget_layout.addWidget(self.api_key, 0, 1)
        # secret key
        bitget_layout.addWidget(QLabel("SecretKey:"), 1, 0)
        secret_key = QLineEdit(bitget.secretkey())
        self.secret_key = secret_key
        bitget_layout.addWidget(self.secret_key, 1, 1)
        # passphrase
        bitget_layout.addWidget(QLabel("Passphrase:"), 2, 0)
        passphrase = QLineEdit(bitget.passphrase())
        self.passphrase = passphrase
        bitget_layout.addWidget(self.passphrase, 2, 1)
        layout.addLayout(bitget_layout)

        # Gate.io
        layout.addWidget(QLabel('Gate.io'))
        gate = GateConfiguration()
        gate_layout = QGridLayout()
        # api key
        gate_layout.addWidget(QLabel("APIKey:"), 0, 0)
        api_key = QLineEdit(gate.apikey())
        self.api_key = api_key
        gate_layout.addWidget(self.api_key, 0, 1)
        # secret key
        gate_layout.addWidget(QLabel("SecretKey:"), 1, 0)
        secret_key = QLineEdit(gate.secretkey())
        self.secret_key = secret_key
        gate_layout.addWidget(self.secret_key, 1, 1)
        layout.addLayout(gate_layout)

        # space
        layout.addItem(QSpacerItem(20, 20))

        # proxy
        proxy_layout = QGridLayout()
        # proxy on/of
        proxy = ProxyConfiguration()
        self.proxy_switch = QRadioButton("VPN代理")
        self.proxy_switch.setChecked(proxy.use_proxy())
        proxy_layout.addWidget(self.proxy_switch, 0, 0)
        # proxy_http
        proxy_layout.addWidget(QLabel("IP"), 1, 0)
        proxy_layout.addWidget(QLabel("Port"), 1, 1)
        proxy_http = QLineEdit(proxy.proxy_ip())
        proxy_port = QLineEdit(str(proxy.proxy_port()))
        self.proxy_ip = proxy_http
        proxy_layout.addWidget(self.proxy_ip, 2, 0)
        self.proxy_port = proxy_port
        proxy_layout.addWidget(self.proxy_port, 2, 1)
        layout.addLayout(proxy_layout)

        # apply button
        btn = QPushButton("应用")
        layout.addWidget(btn)
        btn.clicked.connect(self.accept)

        self.accepted.connect(self._apply_settings)

        # init
        _apply_proxy()

    def _apply_settings(self):
        bitget = BitgetConfiguration()
        bitget.set_apikey(self.api_key.text())
        bitget.set_secretkey(self.secret_key.text())
        bitget.set_passphrase(self.passphrase.text())
        
        gate = GateConfiguration()
        gate.set_apikey(self.api_key.text())
        gate.set_secretkey(self.secret_key.text())

        proxy = ProxyConfiguration()
        proxy.set_use_proxy(self.proxy_switch.isChecked())
        proxy.set_proxy_ip(self.proxy_ip.text())
        proxy.set_proxy_port(int(self.proxy_port.text()))
        _apply_proxy()

