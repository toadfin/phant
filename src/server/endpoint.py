import logging
from collections.abc import Callable

from flask import Flask, request

logger = logging.getLogger("Flask")
endpoints: list[tuple[str, tuple[str], Callable]] = []


def endpoint(url: str, methods: tuple[str, ...] = ("GET",)):
    def outer(callback):
        def wrapper():
            return callback(**request.values)

        endpoints.append((url, methods, wrapper))
        endpoints.append((f"{url}/", methods, wrapper))
        return callback

    return outer


def wrap_app(app: Flask):
    for url, methods, callback in endpoints:
        app.route(url, methods=methods)(callback)

    @app.route('/', defaults={'path': '/'}, methods=["GET", "POST"])
    @app.route('/<path:path>', methods=["GET", "POST"])
    def root(path: str):
        logger.info("NOT IMPLEMENTED - "
                    f"PATH: {path} - "
                    f"PARAMS: {dict(request.values)}")
        return ""
