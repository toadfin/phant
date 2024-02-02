import logging

from flask import Flask

from server import wrap_app

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
wrap_app(app)


if __name__ == "__main__":
    app.run()
