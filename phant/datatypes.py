import json
from typing import Protocol


class Request(Protocol):
    headers: dict[str, str]
    data: bytes
    method: str
    path: str


class Mail:
    def __init__(
            self,
            headers: dict[str, str],
            method: str,
            path: str,
            data: bytes = None,
            data_array: list[int] = None,
    ):
        self.data = data if data is not None else bytes(data_array)
        self._data_array = data_array
        self.headers = headers
        self.method = method
        self.path = path

    @property
    def data_array(self):
        if self._data_array is not None:
            return self._data_array
        else:
            return list(self.data)

    @property
    def content(self):
        return json.loads(self.data.decode())

    def to_dict(self):
        return {
            "headers": self.headers,
            "method": self.method,
            "path": self.path,
            "data_array": self.data_array
        }

    def __repr__(self):
        return f"<{self.__class__.__name__}>"
