import os


class Environ:
    DEBUG = os.environ.get("DEBUG", "true") == "true"
    URL = os.environ.get("URL", "http://127.0.0.1:5000")
