# import logging
import os
from pathlib import Path
import sys

# import traceback
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_cors import CORS
import json
import re
import logging
from api.config import read_tcfg as config

config = config()
# print(config)
# config = read_cfg()['settings']
from api.config import Config
# from api.s3 import s3_init, minio_init

if getattr(sys, 'frozen', False):
    Current_Path = os.path.dirname(sys.executable)
else:
    Current_Path = str(os.path.dirname(__file__))

logger = logging.getLogger("local_api")
logger.propagate = False
# logger.critical("logging init (CRIT)")
level = logging.INFO
logger.setLevel(level=level)
# logging.basicConfig(level=level)
# logger.critical(level)
# logger.critical("logging init 2 (CRIT)")
formatter = logging.Formatter(
    "%(asctime)s :: %(levelname)-8s ::  %(name)s :: %(message)s"
)
console_handler = logging.StreamHandler()
console_handler.setLevel(level=level)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

file_handler = logging.FileHandler(Path(Current_Path) / "local_api.log")
file_handler.setLevel(level=level)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# logger.debug("debug message")
# logger.info("info message")
# logger.warning("warn message")
# logger.error("error message")
# logger.critical("critical message")

# do not change the order of minio and s3 init
# minio = minio_init()
# s3, s3_client = s3_init()
db = SQLAlchemy()


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# if config.get("Debug"):
#     with open(resource_path("uploader_version.txt"), "r") as ver_file:
#         print(ver_file.read())


def format_json(input_dict):
    output = json.dumps(input_dict, sort_keys=False, indent=4, separators=(",", ": "))
    return re.sub(r'",\s+', '", ', output)


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    bcrypt = Bcrypt(app)
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [
                    "https://corems-dev.emsl.pnl.gov",
                    "https://corems.emsl.pnl.gov",
                ],
                "supports_credentials": True,
            }
        },
    )
    app.config.from_object(Config)


    # print(file_handler, stdout_handler)
    # logging.getLogger("flask_cors").level = logging.DEBUG
    # logging.getLogger("flask").level = logging.DEBUG

    # @app.errorhandler(Exception)
    # def handle_http_exception(error):
    #     error_dict = {
    #         "code": error.code,
    #         "description": error.description,
    #         "stack_trace": traceback.format_exc(),
    #     }
    #     log_msg = f"HTTPException {error_dict.code}, Description: {error_dict.description}, Stack trace: {error_dict.stack_trace}"
    #     logger.log(msg=log_msg)
    #     response = jsonify(error_dict)
    #     response.status_code = error.code
    #     return response

    # logging.basicConfig(level=logging.DEBUG)
    # logger = logging.getLogger('corems')

    # blueprint for auth routes in our app
    from api.blueprints.auth_blueprint import auth
    from api.blueprints.instrument_blueprint import instrument

    app.register_blueprint(auth)
    app.register_blueprint(instrument)

    # check_create_buckets(minio, ['fticr-data', 'gcms-data'])

    # @app.context_processor
    # def utility_processor():
    #     def c_version():
    #         return str(__version__)

    #     return dict(current_version=c_version())

    return app
