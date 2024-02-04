import base64
import inspect
import json
import logging
from collections.abc import Callable
from uuid import uuid4

import Crypto.Hash.SHA256
import Crypto.Signature.pkcs1_15
from Crypto.PublicKey import RSA
from flask import Flask, request

from common import Instance, Actor
from environ import Environ

instance = Instance(Environ.INSTANCE)
logger = logging.getLogger("Flask")
endpoints: list[tuple[str, tuple[str], Callable]] = []


def endpoint(
        url: str,
        methods: tuple[str, ...] = ("GET",),
        signed: bool = False,
):
    def outer(callback):
        def wrapper(**kwargs):
            nonlocal url, methods
            if signed:
                error = check_signature()
                if error is not None:
                    return error
            kwargs = dict(request.values, **kwargs)
            for name, param in parameters.items():
                if name not in kwargs and param.default is param.empty:
                    return f"Missing parameter '{name}'.", 422
                elif not isinstance(kwargs[name], param.annotation):
                    return f"Parameter '{name}' should be of type {param.annotation}.", 422
            logger.info(f"{request.method} {request.path}, KWARGS: {kwargs}")
            response = callback(**kwargs)
            if response is None:
                response = ""
            elif isinstance(response, bool):
                response = json.dumps(response)
            return response

        parameters = inspect.signature(callback).parameters
        endpoints.append((url, methods, wrapper))
        endpoints.append((f"{url}/", methods, wrapper))
        return callback

    return outer


def wrap_app(app: Flask):
    for url, methods, callback in endpoints:
        app.add_url_rule(url, f"{url}-{methods}-{uuid4()}", view_func=callback, methods=methods)

    @app.route('/', defaults={'path': '/'}, methods=["GET", "POST"])
    @app.route('/<path:path>', methods=["GET", "POST"])
    def root(path: str):
        logger.info(f"NOT IMPLEMENTED: {request.method} {path}")
        return "Not implemented", 501


def check_signature():
    for header in ("Digest", "Host", "Date", "Signature"):
        if header not in request.headers:
            return f"Missing Header: {header}", 401
    if request.headers["Host"] != instance.hostname:
        return f"Invalid Header: Host", 401
    hasher = Crypto.Hash.SHA256.new()
    hasher.update(request.data)
    digest = "sha-256=" + base64.b64encode(hasher.digest()).decode("ascii")
    if request.headers["Digest"] != digest:
        return f"Invalid Header: Digest", 401
    actor = signature_hash = signature = None
    for field in request.headers["Signature"].split(","):
        name, value = field.split("=")
        value = value[1:-1]
        if name == "keyId":
            actor = Actor.url(value)
        elif name == "headers":
            signed_string = []
            for header in value.split(" "):
                if header == "(request-target)":
                    signed_string.append(f"(request-target): {request.method.lower()} {request.path}")
                elif header == "digest":
                    signed_string.append(f"digest: {digest}")
                elif header == "host":
                    signed_string.append(f"host: {instance.hostname}")
                elif header == "date":
                    signed_string.append(f"date: {request.headers['Date']}")
                else:
                    return f"Invalid header name in field headers of Signature header: {header}", 401
            signed_string = "\n".join(signed_string)
            signature_hash = Crypto.Hash.SHA256.new()
            signature_hash.update(signed_string.encode("ascii"))
        elif name == "signature":
            signature = base64.b64decode(value)
        else:
            return f"Invalid field in Signature header: {name}", 401
    for name, field in {"keyId": actor, "headers": signature_hash, "signature": signature}.items():
        if field is None:
            return f"Missing field in Signature header: {name}", 401
    signer = Crypto.Signature.pkcs1_15.new(RSA.import_key(actor.public_key_pem))
    try:
        signer.verify(signature_hash, signature)
    except ValueError:
        return "Invalid signature", 403
