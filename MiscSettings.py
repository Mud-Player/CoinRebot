from PySide6 import QtWidgets
from PySide6.QtCore import QSettings
from PySide6.QtNetwork import QNetworkProxy
from PySide6.QtWidgets import QLabel, QLineEdit, QSpacerItem, QRadioButton, QPushButton


class Configurations:
    settings = QSettings("Li.Player", "BitGetBox")

    def __init__(self):
        pass

    def __del__(self):
        Configurations.settings.sync()

    @staticmethod
    def apikey():
        return str(Configurations.settings.value("APIKey", ""))

    @staticmethod
    def set_apikey(value):
        Configurations.settings.setValue("APIKey", value)

    @staticmethod
    def secretkey():
        return str(Configurations.settings.value("Secretkey", ""))

    @staticmethod
    def set_secretkey(value):
        Configurations.settings.setValue("Secretkey", value)

    @staticmethod
    def passphrase():
        return str(Configurations.settings.value("Passphrase", ""))

    @staticmethod
    def set_passphrase(value):
        Configurations.settings.setValue("Passphrase", value)

    @staticmethod
    def use_proxy():
        return bool(Configurations.settings.value("use_proxy", False, type=bool))

    @staticmethod
    def set_use_proxy(value):
        Configurations.settings.setValue("use_proxy", value)

    @staticmethod
    def proxy_ip():
        return str(Configurations.settings.value("proxy_ip", "127.0.0.1"))

    @staticmethod
    def set_proxy_ip(value):
        Configurations.settings.setValue("proxy_ip", value)

    @staticmethod
    def proxy_port() -> int:
        value = Configurations.settings.value("proxy_port", defaultValue=1080, type=int)
        return value

    @staticmethod
    def set_proxy_port(value: int):
        Configurations.settings.setValue("proxy_port", value)


class MiscSettingWidget(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        layout = QtWidgets.QGridLayout(self)
        # api key
        layout.addWidget(QLabel("APIKey:"), 0, 0)
        api_key = QLineEdit(Configurations.apikey())
        self.api_key = api_key
        layout.addWidget(self.api_key, 0, 1)
        # secret key
        layout.addWidget(QLabel("SecretKey:"), 1, 0)
        secret_key = QLineEdit(Configurations.secretkey())
        self.secret_key = secret_key
        layout.addWidget(self.secret_key, 1, 1)

        # passphrase
        layout.addWidget(QLabel("Passphrase:"), 2, 0)
        passphrase = QLineEdit(Configurations.passphrase())
        self.passphrase = passphrase
        layout.addWidget(self.passphrase, 2, 1)

        # space
        layout.addItem(QSpacerItem(20, 20), 3, 0)

        # proxy on/of
        self.proxy_switch = QRadioButton("VPN代理")
        self.proxy_switch.setChecked(Configurations.use_proxy())
        layout.addWidget(self.proxy_switch, 4, 0)

        # proxy_http
        layout.addWidget(QLabel("IP"), 5, 0)
        layout.addWidget(QLabel("Port"), 5, 1)
        proxy_http = QLineEdit(Configurations.proxy_ip())
        proxy_port = QLineEdit(str(Configurations.proxy_port()))
        self.proxy_ip = proxy_http
        layout.addWidget(self.proxy_ip, 6, 0)
        self.proxy_port = proxy_port
        layout.addWidget(self.proxy_port, 6, 1)

        # apply button
        btn = QPushButton("应用")
        layout.addWidget(btn, 7, 0, 1, 2)
        btn.clicked.connect(self.accept)

        self.accepted.connect(self._apply_settings)

        # init
        self._apply_proxy()

    def _apply_settings(self):
        Configurations.set_apikey(self.api_key.text())
        Configurations.set_secretkey(self.secret_key.text())
        Configurations.set_passphrase(self.passphrase.text())
        Configurations.set_use_proxy(self.proxy_switch.isChecked())
        Configurations.set_proxy_ip(self.proxy_ip.text())
        Configurations.set_proxy_port(int(self.proxy_port.text()))
        self._apply_proxy()

    def _apply_proxy(self):
        if Configurations.use_proxy():
            proxy = QNetworkProxy(QNetworkProxy.ProxyType.HttpProxy,
                                  Configurations.proxy_ip(), Configurations.proxy_port())
            QNetworkProxy.setApplicationProxy(proxy)
        else:
            proxy = QNetworkProxy(QNetworkProxy.ProxyType.NoProxy)
            QNetworkProxy.setApplicationProxy(proxy)

