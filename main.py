from api import create_app, config
import sys
from pathlib import Path
import os

app = create_app()

# current_version: str = "0.1.1-dev70"
current_version: str = "1.0.1.106"

if getattr(sys, "frozen", False):
    # we are running in a bundle
    bundle_dir = sys._MEIPASS
else:
    # we are running in a normal Python environment
    bundle_dir = os.path.dirname(os.path.abspath(__file__))


def server():
    from waitress import serve
    import logging

    # logger = logging.getLogger("waitress")
    logger = logging.getLogger("local_api")
    # logger.setLevel(logging.WARN)
    logger.info("Uploader version: %s", current_version)
    logger.info("Waiting for connection")
    print(
        """
______                   _         _ 
| ___ \                 | |       | |
| |_/ /  ___   __ _   __| | _   _ | |
|    /  / _ \ / _` | / _` || | | || |
| |\ \ |  __/| (_| || (_| || |_| ||_|
\_| \_| \___| \__,_| \__,_| \__, |(_)
                             __/ |   
                            |___/    
"""
    )
    serve(
        app,
        host="127.0.0.1",
        expose_tracebacks=True,
        port=(config["ListenPort"] or 8000),
        threads=8,
    )


def upload():
    from upload_self_to_minio import minio_upload

    minio_upload()


if __name__ == "__main__":
    if sys.argv[-1] == "--upload" and Path("../dist"):
        upload()
        sys.exit(0)
    if sys.argv[-1] in ("--version", "-v"):
        print(current_version)
        sys.exit(0)
    # if sys.argv[-1] == "--update":
    #     update()
    else:
        server()
