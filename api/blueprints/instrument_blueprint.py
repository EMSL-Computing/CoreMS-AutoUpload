import json
from datetime import datetime
from time import sleep
import persistqueue

import requests
from api import config
from api.blueprints.auth_blueprint import token_required
from api.scanner import RawQCWatcher
from flask import Blueprint, request
import logging

logger = logging.getLogger("local_api")
corems_url = config["API_URI"]

instrument = Blueprint("instrument", __name__)


@instrument.route("/api/instrument/identifier")  # type: ignore
def return_machine_name():
    return request.form.get("select") or config.get("InstrumentName")


@instrument.route("/api/instrument/stop", methods=["POST"])
@token_required
def stop_scan_instrument(current_user, payload=None):
    # data will come from form to json from corems ajax call,
    # print(request.form.get("select"))
    payload = {
        # "id": 2,
        "name": request.form.get("select") or config.get("InstrumentName"),
        "state": "stop",
        "time_stamp": datetime.utcnow(),
    }

    instrument_name = payload["name"]

    # update state
    api_url = f"/instrument/{instrument_name}"
    headers = {
        "x-access-tokens": current_user.auth_token,
        "Content-Type": "application/json",
    }
    r = requests.put(
        url=corems_url + api_url, data=json.dumps(payload, default=str), headers=headers
    )
    if r.status_code == 200:
        response_obj = {
            "status": "success",
            "message": "Instrument {} flagged to stop scanning".format(instrument_name),
        }
        return response_obj
    else:
        response_obj = {
            "status": "fail",
            "message": "Instrument {} was not flagged to stop scanning".format(
                instrument_name
            ),
            "result code": r.status_code,
        }
        return response_obj, 500


@instrument.route("/api/instrument/start", methods=["POST"])  # type: ignore
@token_required
def scan_instrument(current_user):
    logger.info("entered scan")
    # data will come from form to json from corems ajax call,
    # instrument_id, instrument_state
    data = {}
    logger.info(request.form)
    # defaultData["id"] = 2
    data["name"] = request.form.get("select") or config.get("InstrumentName")
    data["state"] = "scanning"
    data["time_stamp"] = datetime.utcnow()
    data["acquisition_path"] = config.get("WatchedPath")
    data["parameters_id"] = request.form.get("methodselect")
    logger.info("%s ; %s", data["name"], request.form.get("select"))
    token = current_user.auth_token
    transient_timeout = request.form.get("interval") or None
    try:
        logger.info("entered try")
        if config.get("ScanStatus"):
            response_obj = {
                "status": config.get("ScanStatus"),
                "message": "Instrument {} is already scanning for data".format(
                    data["name"]
                ),
            }
            return response_obj
    except KeyError as e:
        logger.warn(e)
    scanner = RawQCWatcher(
        acquisition_path=data["acquisition_path"],
        instrument_name=data["name"],
        user_id=current_user.id,
        parameters_id=int(data["parameters_id"]),
        token=token,
        transient_timeout=transient_timeout,
    )
    api_url = f"/instrument/{data['name']}"
    logger.info(api_url)
    headers = {"x-access-tokens": token, "Content-Type": "application/json"}

    del data["parameters_id"]
    for _ in range(2):
        logger.info("before put loop 1")
        logger.info(
            "data %s, %s \nheaders %s", data, json.dumps(data, default=str), headers
        )
        r = requests.put(
            url=corems_url + api_url,
            data=json.dumps(data, default=str),
            headers=headers,
        )
        if r.status_code == 200:
            response_obj = {
                "status": "success",
                "message": "Instrument {} is scanning for data".format(data["name"]),
            }
            scanner.start()
            return response_obj
        elif r.status_code == 404:
            requests.post(
                url=corems_url + "/instrument/",
                data=json.dumps(data, default=str),
                headers=headers,
            )
            logger.info("Instrument created, please restart scan; code: %s", r.status_code)
            sleep(0.5)
            return r.text
        else:
            logger.info("not 200 or 404, status was %s: %s", r.status_code, r.text)
            return r.text


@instrument.route("/api/instrument/status")
def return_machine_status():
    status = config.get("ScanStatus")
    return str(status) if status else "Prestart"


@instrument.route("/api/instrument/queue")
def return_local_queue():
    queue_path = "./queue_test"
    queue: persistqueue.UniqueAckQ = persistqueue.UniqueAckQ(
        path=queue_path, multithreading=True
    )
    return [i for i in queue.queue() if i["status"] != 5]
