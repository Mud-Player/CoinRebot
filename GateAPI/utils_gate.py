import hashlib
import hmac
import time


def gen_sign(api_key, api_secret, timestamp_s, method, url, query_string=None, payload_string=None):
    sha = hashlib.sha512()
    sha.update((payload_string or "").encode('utf-8'))
    hashed_payload = sha.hexdigest()
    s = '%s\n%s\n%s\n%s\n%s' % (method, url, query_string or "", hashed_payload, timestamp_s)
    sign = hmac.new(api_secret.encode('utf-8'), s.encode('utf-8'), hashlib.sha512).hexdigest()
    return {'KEY': api_key, 'Timestamp': str(timestamp_s), 'SIGN': sign}
