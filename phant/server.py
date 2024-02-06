import inspect
import json
import logging
from collections.abc import Callable
from uuid import uuid4

from flask import Flask, request

from .auth import verify_request
from .instance import Instance

phant_instance: list[Instance] = []
logger = logging.getLogger("Server")
endpoints: list[tuple[str, tuple[str], Callable]] = []


def endpoint(
        url: str,
        methods: tuple[str, ...] = ("GET",),
        signed: bool = False,
):
    def decorator(callback):
        def wrapper(**kwargs):
            if signed:
                error = verify_request(phant_instance[0], request)
                if error is not None:
                    log(error[0])
                    return error
            kwargs = dict(request.values, **kwargs)
            for name, param in parameters.items():
                if name not in kwargs and param.default is param.empty:
                    log(f"Missing parameter '{name}'.")
                    return f"Missing parameter '{name}'.", 422
                elif not isinstance(kwargs[name], param.annotation):
                    log(f"Parameter '{name}' should be of type {param.annotation}.")
                    return f"Parameter '{name}' should be of type {param.annotation}.", 422
            response = callback(**kwargs)
            if response is None:
                response = ""
            elif isinstance(response, bool):
                response = json.dumps(response)
            log("OK")
            return response

        parameters = inspect.signature(callback).parameters
        endpoints.append((url, methods, wrapper))
        endpoints.append((f"{url}/", methods, wrapper))
        return callback

    return decorator


def wrap_flask_app(instance: str, app: Flask):
    phant_instance.append(Instance(instance))

    for url, methods, callback in endpoints:
        app.add_url_rule(url, f"{url}-{methods}-{uuid4()}", view_func=callback, methods=methods)

    @app.route('/', defaults={'path': '/'}, methods=["GET", "POST"])
    @app.route('/<path:path>', methods=["GET", "POST"])
    def root(path: str):
        log(f"NOT IMPLEMENTED - {path}")
        return "Not implemented", 501


def log(message: str):
    logger.info(f"{request.method} {request.path} {dict(request.values)} - {message}")
