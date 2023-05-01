import os
import configparser
from pathlib import Path
import shutil
import sys
from typing import Dict

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


class Config:

    SECRET_KEY = os.environ.get("SECRET_KEY")
    UPLOAD_FOLDER = f"{os.getenv('APP_FOLDER')}/app/data"

    directory = os.getcwd()

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SESSION_TYPE = os.environ.get("SESSION_TYPE") or "memcached"

    # keycloak_login_url = (
    #     ""
    # )
    keycloak_client_id = "corems"
    keycloak_realm_name = "nexus"
    keycloak_client_secret_key = "oauth2_proxy"


def read_cfg(infile="config.ini"):
    config = configparser.RawConfigParser()
    with open(infile) as configfile:
        config.read_file(configfile)
    return config


def read_tcfg(infile="config.toml") -> Dict:
    # print(Path.cwd())
    # config = configparser.RawConfigParser()
    try:
        if Path(infile).exists():
            pass
        with open(infile, "rb") as configfile:
            config = tomllib.load(configfile)
    except FileNotFoundError:
        print("No config file found, copying example to use")
        shutil.copy("config.toml.example", infile)
        sys.exit(1)
    # finally:
    #     pass
    return config["settings"]

