import logging

from flask import Flask, request


logger = logging.getLogger("Main")
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)


@app.route('/', defaults={'path': '/'}, methods=["GET", "POST"])
@app.route('/<path:path>', methods=["GET", "POST"])
def root(path: str):
    logger.info("NOT IMPLEMENTED - "
                f"PATH: {path} - "
                f"PARAMS: {dict(request.values)}")
    return ""


if __name__ == "__main__":
    app.run()
