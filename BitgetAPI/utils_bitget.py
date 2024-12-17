import base64
import hmac
import time

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5 as pkcs1
import BitgetAPI.consts_bitget as const


def sign(message, secret_key):
    mac = hmac.new(bytes(secret_key, encoding='utf8'), bytes(message, encoding='utf-8'), digestmod='sha256')
    d = mac.digest()
    return str(base64.b64encode(d), 'utf8')

def signByRSA(message, secret_key):
    private_key = RSA.importKey(secret_key)
    h = SHA256.new(message.encode('utf-8'))
    signer = pkcs1.new(private_key)
    sign_ = signer.sign(h)
    return str(base64.b64encode(sign_), 'utf8')


def pre_hash(timestamp, method, request_path, body = ""):
    return str(timestamp) + str.upper(method) + request_path + body


def get_header(api_key, sign_, timestamp, passphrase):
    header = dict()
    header[const.CONTENT_TYPE] = const.APPLICATION_JSON
    header[const.OK_ACCESS_KEY] = api_key
    header[const.OK_ACCESS_SIGN] = sign_
    header[const.OK_ACCESS_TIMESTAMP] = str(timestamp)
    header[const.OK_ACCESS_PASSPHRASE] = passphrase
    header[const.LOCALE] = 'zh-CN'

    return header

def toQueryWithNoEncode(params):
    url = ''
    for key, value in params:
        url = url + str(key) + '=' + str(value) + '&'
    return url[0:-1]

def signature(timestamp, method, request_path, body, secret_key):
    if str(body) == '{}' or str(body) == 'None':
        body = ''
    message = str(timestamp) + str.upper(method) + request_path + str(body)
    mac = hmac.new(bytes(secret_key, encoding='utf8'), bytes(message, encoding='utf-8'), digestmod='sha256')
    d = mac.digest()
    return base64.b64encode(d)

def check_none(value, msg=""):
    if not value:
        raise Exception(msg + " Invalid params!")