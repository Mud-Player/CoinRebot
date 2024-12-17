import hashlib
import hmac
import time
from urllib.parse import urlencode


def gen_signed_body(api_secret, timestamp, params: dict):
    _params = params.copy()
    _params['timestamp'] = timestamp
    params_url = urlencode(_params)
    sign = hmac.new(api_secret.encode('utf-8'), params_url.encode('utf-8'), hashlib.sha256).hexdigest()
    params_url += f'&signature={sign}'
    return params_url