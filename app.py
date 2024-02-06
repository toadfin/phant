import logging

from flask import Flask

from environ import Environ
from phant import wrap_flask_app

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
wrap_flask_app(Environ.INSTANCE, app)


if __name__ == "__main__":
    app.run()
