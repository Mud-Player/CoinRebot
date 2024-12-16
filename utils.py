import time

from PySide6.QtNetwork import QNetworkRequest


def get_timestamp():
    return int(time.time() * 1000)

def setup_header(headers, request: QNetworkRequest):
    for key, value in headers.items():
        request.setRawHeader(key.encode(), value.encode())  # `encode()` 将字符串转换为字节