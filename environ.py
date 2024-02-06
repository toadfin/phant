import os


class Environ:
    INSTANCE: str = os.environ.get("INSTANCE_URL", "127.0.0.1:5000")
