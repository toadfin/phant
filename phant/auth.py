import base64
import datetime

import Crypto.Hash.SHA256
import Crypto.Signature.pkcs1_15
import requests
from Crypto.PublicKey.RSA import RsaKey

from .actor import Actor
from .datatypes import Request
from .instance import Instance


def signed_request(
        method: str,
        endpoint: str,
        sender: Actor,
        content: str = "",
        date: datetime.datetime = None,
        **kwargs
):
    url = Instance(endpoint)
    date = (date or datetime.datetime.utcnow()).strftime("%a, %d %b %Y %H:%M:%S GMT")
    digest = "sha-256=" + _do_digest(content)
    signed_string = f"(request-target): {method.lower()} {url.path}\n" \
                    f"digest: {digest}\n" \
                    f"host: {url.hostname}\n" \
                    f"date: {date}"
    signature_header = f'keyId="{sender.public_key_id}",' \
                       f'headers="(request-target) digest host date",' \
                       f'signature="{_do_sign(signed_string, sender.private_key)}"'
    if "headers" in kwargs:
        headers = kwargs["headers"]
        del kwargs["headers"]
    else:
        headers = {}
    return requests.request(method, endpoint, data=content, headers=dict(
        headers,
        Digest=digest,
        Host=url.hostname,
        Date=date,
        Signature=signature_header
    ), **kwargs)


class RequestsVerifier:
    def __init__(self):
        self._keys = {}

    def set_key(self, public_key_id: str, public_key: RsaKey):
        self._keys[public_key_id] = public_key

    def get_key(self, public_key_id: str):
        return self._keys[public_key_id]

    def verify(self, instance: Instance, request: Request):
        for header in ("Digest", "Host", "Date", "Signature"):
            if header not in request.headers:
                return f"Missing Header: {header}", 401
        if request.headers["Host"] != instance.hostname:
            return f"Invalid Host Header: {request.headers['Host']} should be {instance.hostname}", 401
        parts = request.headers["Digest"].split('=', maxsplit=1)
        if len(parts) != 2:
            return f"Invalid Digest Header"
        if parts[0].lower() != "sha-256":
            return f"Digest Header uses {parts[0]} instead of sha-256", 401
        digest = _do_digest(request.data.decode())
        if parts[1] != digest:
            return f"Invalid Header: Digest", 401
        signature_fields = {}
        for field in request.headers["Signature"].split(","):
            item = field.split("=", maxsplit=1)
            if len(item) != 2 or len(item[1]) < 2 or not item[1].startswith('"') or not item[1].endswith('"'):
                return "Invalid field in Signature Header: " + request.headers["Signature"], 401
            signature_fields[item[0]] = item[1][1:-1]
        for field in ("keyId", "headers", "signature"):
            if field not in signature_fields:
                return f"Missing field in Signature header: {field}", 401
        public_key = self._keys.get(signature_fields["keyId"])
        if public_key is None:
            return "No available key for actor " + signature_fields["keyId"], 401
        signed_string = []
        for header in signature_fields["headers"].split(" "):
            if header == "(request-target)":
                signed_string.append(f"(request-target): {request.method.lower()} {request.path}")
            elif header == "digest":
                signed_string.append(f"digest: {request.headers['Digest']}")
            elif header == "host":
                signed_string.append(f"host: {instance.hostname}")
            elif header == "date":
                signed_string.append(f"date: {request.headers['Date']}")
            elif header == "content-type":
                signed_string.append(f"content-type: {request.content_type}")
            else:
                return f"Invalid header name in field headers of Signature header: {header}", 401
        signed_string = "\n".join(signed_string)
        if not _do_verify(signed_string, signature_fields["signature"], public_key):
            return "Invalid signature", 403


def _do_sign(value: str, private_key: RsaKey) -> str:
    value = _do_hash(value)
    signer = Crypto.Signature.pkcs1_15.new(private_key)
    return base64.b64encode(signer.sign(value)).decode()


def _do_verify(value: str, signature: str, public_key: RsaKey):
    hasher = _do_hash(value)
    signature = base64.b64decode(signature)
    signer = Crypto.Signature.pkcs1_15.new(public_key)
    try:
        signer.verify(hasher, signature)
        return True
    except ValueError:
        return False


def _do_digest(value: str) -> str:
    hasher = _do_hash(value)
    return base64.b64encode(hasher.digest()).decode()


def _do_hash(value: str):
    hasher = Crypto.Hash.SHA256.new()
    hasher.update(value.encode())
    return hasher
