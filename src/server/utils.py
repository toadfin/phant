import inspect
import logging
from collections.abc import Callable
from uuid import uuid4

from flask import Flask, request

logger = logging.getLogger("Flask")
endpoints: list[tuple[str, tuple[str], Callable]] = []


def endpoint(url: str, methods: tuple[str, ...] = ("GET",)):
    def outer(callback):
        def wrapper(**kwargs):
            kwargs = dict(request.values, **kwargs)
            for name, param in parameters.items():
                if name not in kwargs and param.default is param.empty:
                    return f"Missing parameter '{name}'.", 422
                elif not isinstance(kwargs[name], param.annotation):
                    return f"Parameter '{name}' should be of type {param.annotation}.", 422
            return callback(**kwargs)

        parameters = inspect.signature(callback).parameters
        endpoints.append((url, methods, wrapper))
        endpoints.append((f"{url}/", methods, wrapper))
        return callback

    return outer


def wrap_app(app: Flask):
    for url, methods, callback in endpoints:
        app.add_url_rule(url, str(uuid4()), view_func=callback, methods=methods)

    @app.route('/', defaults={'path': '/'}, methods=["GET", "POST"])
    @app.route('/<path:path>', methods=["GET", "POST"])
    def root(path: str):
        logger.info("NOT IMPLEMENTED - "
                    f"PATH: {path} - "
                    f"PARAMS: {dict(request.values)}")
        return ""
