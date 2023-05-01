import datetime
import json
from pathlib import Path
import pprint
import threading
import time
from typing import Any
import jwt
import requests
import pause

# from api import minio
from api.s3 import minio_init
from api import config
from watchdog.observers import Observer
from watchdog.events import RegexMatchingEventHandler
import sys
import os
import clr
import persistqueue
import logging
from upload_self_to_minio import Progress


logger = logging.getLogger("local_api")

sys.path.append("ext_lib")
clr.AddReference("ThermoFisher.CommonCore.RawFileReader")
from ThermoFisher.CommonCore.RawFileReader import RawFileReaderAdapter


corems_url: str = config["API_URI"]


class FtmsQcEventHandler(RegexMatchingEventHandler):
    default_regex = []
    logger.info("default regex init: %s", default_regex)
    if config.get("WatchedRegex"):
        default_regex.append(r"{}".format(config.get("WatchedRegex")))
    else:
        default_regex.append(r"^(?!x_).*(?:_SRFA).*.(?:raw|d)$")

    RAW_FILE_REGEX = default_regex
    logger.info("regex set to: %s", RAW_FILE_REGEX)

    def __init__(self, queue):
        super().__init__(regexes=self.RAW_FILE_REGEX)
        self.queue: persistqueue.SQLiteAckQueue = queue

    def on_created(self, event) -> None:
        filepath: Path = Path(event.src_path)
        if (".d" in filepath.suffix and filepath.is_dir()) or ".raw" in filepath.suffix:
            logger.info("file creation event observed %s", event)
            self.add_to_local_queue(event)
        # pass

    def on_modified(self, event) -> None:
        pass

    def add_to_local_queue(self, event) -> None:
        # print("added " + str(event) + " to queue")
        logger.info("added %s to queue", event)
        self.queue.put(event)


class LocalWorker:
    def __init__(self, token, user_id, parameters_id, transient_timeout, queue) -> None:
        self.user_id = user_id
        self.parameters_id = parameters_id
        self.transient_timeout = (
            transient_timeout or config.get("TransientTimeout") or 10
        )
        self.api_header = {"x-access-tokens": token, "Content-Type": "application/json"}
        self.queue = queue
        self.minio = minio_init()

    def process_local_queue(self) -> None:
        run: bool = config["ScanStatus"]
        try:
            while run:
                run = config["ScanStatus"]
                event = self.queue.get()
                logger.info("got event")
                if self.check_if_complete(event):
                    self.queue.ack(event)
                else:
                    logging.warning("File not complete, returning to queue.")
                    self.queue.nack(event)
        except Exception as error:
            logger.warning(error)

    def check_if_complete(self, event):
        filepath = Path(event.src_path)
        logger.info("%s %s", filepath, filepath.suffix)
        if ".raw" in filepath.suffix:
            time.sleep(2)
            logger.info("Found raw file, sleeping 2 sec")
            try:
                iRawDataPlus = RawFileReaderAdapter.FileFactory(str(filepath))
                if iRawDataPlus.InAcquisition:
                    time.sleep(5)
                    return False
                self.process(event)
                return True
            except:
                return False
            finally:
                iRawDataPlus.Dispose()

        if ".d" in filepath.suffix and filepath.is_dir():
            # pass
            transient = ("ser", "fid")
            data_times = []
            data_time_delta = None
            for _ in range(0, 330):  # >50 minutes?
                try:
                    trans_file = [
                        filepath / i for i in transient if (filepath / i).is_file()
                    ][0]
                    time.sleep(1)
                    if trans_file:
                        data_times.append(datetime.datetime.now())
                        logger.info("Transient file found, time was %s", data_times[-1])
                        if trans_file.stat().st_size > 0:
                            data_times.append(datetime.datetime.now())
                            # logger.info("data appearance time was %s", data_appearence_time)
                            data_time_delta = data_times[-1] - data_times[0]
                            logger.info("data found, proceeding")
                            logger.info(
                                "data took %s seconds to appear", data_time_delta
                            )
                            data_times = []
                            break
                        else:
                            logger.error(
                                "didn't find data in transient for %s, sleeping 10 sec",
                                filepath,
                            )
                            time.sleep(10)
                except IndexError:
                    logger.error(
                        "didn't find transient for %s, sleeping 10 sec", filepath
                    )
                    time.sleep(10)

            if trans_file and trans_file.stat().st_size > 0:
                logger.info("sleeping ten second before checking lockedness of FID/SER")
                locked = True
                time.sleep(10)
                while locked:
                    try:
                        with open(trans_file, "a") as _:
                            logger.info("%s now unlocked", trans_file)
                            locked = False
                            pass
                    except IOError:
                        time.sleep(2)

            logger.info(
                "Transient timeout set, waiting %s seconds to proceed.",
                self.transient_timeout,
            )
            time.sleep(self.transient_timeout)
            logger.info("trans_file is %s", trans_file)
            snapshot = os.stat(trans_file)
            logger.info(
                "snapshot was %s, sleeping %s sec",
                snapshot,
                (data_time_delta.total_seconds() + 5),
            )
            time.sleep(data_time_delta.total_seconds() + 5)
            delta = os.stat(trans_file)
            logger.info("delta was %s", delta)
            if snapshot == delta:
                logger.info("snapshot == delta, processing!")
                self.process(event)
                return True

    def process(self, event):
        # check for tag on raw file to finished acquisition
        logger.info("Processing ")
        filepath = Path(event.src_path)
        logger.info("filepath: %s", filepath)
        # upload data and add new data to db,
        # make sure to add group to respective instrument QC and get dataId
        dataId = self.upload_data_to_corems(filepath)
        logger.info("dataId: %s", dataId)
        #  send data with minio and hit corems process end point
        logger.info("adding to runner queue")
        self.add_workflow_to_remote_queue(dataId)

    def upload_data_to_corems(self, src_path: Path):
        # send data to api to correct name to duplicate name
        # FIXME
        access_group = "QC_12T_FTICR"
        src_path = Path(src_path)
        api_url = f"/ftms/data/{self.user_id}"
        s3_path = f"{self.user_id}/{src_path.name}"

        data = {
            "filepath": s3_path,
            "name": src_path.stem,
            "modifier": "",
            "is_centroid": False,
        }
        r = requests.put(
            corems_url + api_url, headers=self.api_header, data=json.dumps(data)
        )
        response_json = r.json()
        dataId = response_json["id"]
        corrected_s3_path = response_json["filepath"]

        # check and create AccessGroup
        api_url = f"/access/group/{access_group}"
        r = requests.get(corems_url + api_url, headers=self.api_header)
        if r.status_code == 200:
            groupId = r.json()["id"]
        else:
            api_url = f"/access/group/{access_group}"
            r = requests.post(corems_url + api_url, headers=self.api_header)
            groupId = r.json()["id"]

        # create FTMS_DataAccessLink
        api_url = f"/ftms/access/{dataId}/{groupId}"
        r = requests.post(corems_url + api_url, headers=self.api_header)

        # upload data to minio
        progress = Progress() if config.get("ShowProgress") else None
        if src_path.is_dir():
            depth = len(src_path.parts)
            files = src_path.rglob("*")
            for file in sorted(files):
                if file.is_file():
                    rel_path = Path(*file.parts[depth:])
                    rel_path = str(rel_path).replace(os.sep, "/")
                    remote_dest = corrected_s3_path + "/" + rel_path
                    # print(file, rel_path)
                    self.minio.fput_object(
                        "fticr-data",
                        remote_dest,
                        str(file),
                        part_size=64 * 1024 * 1024,
                        progress=progress,
                    )
            return dataId

        if src_path.is_file():
            self.minio.fput_object(
                "fticr-data",
                corrected_s3_path,
                str(src_path),
                progress=progress,
            )
            return dataId

    def add_workflow_to_remote_queue(self, data_id: int):
        #  add data to queue using corems api
        api_url = f"/ftms/workflow/qc/{self.user_id}"

        payload = {
            "parameters_id": self.parameters_id,
            "cal_data_id": None,
            "data_ids": [data_id],
        }
        logger.info(payload)
        r = requests.post(
            corems_url + api_url, headers=self.api_header, data=json.dumps(payload)
        )
        logger.info("api_url: %s, payload:%s, r.text %s", api_url, payload, r.text)
        return r


class RawQCWatcher:
    def __init__(
        self,
        acquisition_path,
        instrument_name,
        user_id,
        parameters_id,
        token,
        transient_timeout,
        interval=10,
        queue_path="./queue_test",
    ):
        self.queue: persistqueue.UniqueAckQ = persistqueue.UniqueAckQ(
            path=queue_path, multithreading=True
        )
        self.__src_path = acquisition_path
        self.__event_handler: FtmsQcEventHandler = FtmsQcEventHandler(self.queue)
        self.__event_observer = Observer()
        self.__worker: LocalWorker = LocalWorker(
            token, user_id, parameters_id, transient_timeout, self.queue
        )
        self.instrument_name = instrument_name
        self.token = token
        self.checker = None
        self.worker = None
        self.token_checker = None
        self.run = False
        config["ScanStatus"] = self.run
        self.interval: int = int(config.get("KeepAliveInterval")) or interval

    def start(self):
        if self.run:
            return "Already running"
        logger.info("Received start signal...")
        self.__start()
        logger.info("starting checker...")
        self.checker = threading.Thread(
            name="background monitor", target=self.check_remote
        )
        self.checker.start()
        logger.info("Checker started!")
        logger.info("starting workers...")
        for i in range(4):
            t: threading.Thread = threading.Thread(target=self.__worker.process_local_queue)
            t.daemon = True
            logger.info("worker %i initialized", i)
            t.start()
            logger.info("worker %i started!", i)
        logger.info("starting token checker...")
        self.token_checker = threading.Thread(
            name="token checker", target=self.token_refresh_check
        )
        self.token_checker.start()
        logger.info("Token checker started!")
        logger.info("All Components Started!")

    def stop(self):
        logger.info("Received stop signal")
        self.__stop()
        self.run = False
        config["ScanStatus"] = self.run
        self.queue.clear_acked_data()
        self.queue.shrink_disk_usage()
        logger.info("slept, cleaned, shrunk queue")
        logger.info("Stopped")

    def status(self):
        return "Running" if self.run else "Stopped"

    def __status(self) -> bool:
        return True if self.run else False

    def queue_items(self) -> "list[Any]":
        return [i for i in self.queue.queue() if i["status"] != 5]

    def token_refresh_check(self):
        from api.config import Config as fconfig

        key = fconfig.SECRET_KEY
        alg = ["HS256"]

        token = self.token
        decode_token = jwt.decode(token, key, algorithms=alg)
        exp_time: datetime.datetime = datetime.datetime.fromtimestamp(
            decode_token["exp"]
        )
        # print(exp_time)
        while self.run:
            current_time = datetime.datetime.utcnow()
            if (exp_time - current_time).seconds <= 3600:
                logger.info("token nearing expiration, refreshing")
                new_payload = {
                    "exp": datetime.datetime.utcnow()
                    + datetime.timedelta(days=1, seconds=5),
                    "iat": datetime.datetime.utcnow(),
                    "id": decode_token.id,
                    "first_name": decode_token.first_name,
                    "last_name": decode_token.last_name,
                    "email": decode_token.email,
                }
                new_token = jwt.encode(new_payload, key=key, algorithm=alg)
                self.token = new_token
            else:
                pause.minutes(1)

    def check_remote(self):
        api_url = f"/instrument/{self.instrument_name}"
        headers = {"x-access-tokens": self.token, "Content-Type": "application/json"}
        try:
            self.run = True
            config["ScanStatus"] = self.run
            while self.run:
                r = requests.get(corems_url + api_url, headers=headers)
                try:
                    if config["Debug"]:
                        logger.info(self.status())
                        if self.queue_items():
                            logger.info("Enqueued Files: ")
                            for line in pprint.pformat(self.queue_items()).split("\n"):
                                logger.info(line)
                except KeyError:
                    pass
                if r.status_code == 200:
                    instrument_obj = r.json()
                    if instrument_obj["state"] == "stop":
                        # update state to idle
                        instrument_obj["state"] = "idle"
                        instrument_obj["time_stamp"] = datetime.datetime.utcnow()
                        # submit change to corems api
                        r = requests.put(
                            corems_url + api_url, headers=headers, data=instrument_obj
                        )
                        break
                    time.sleep(int(self.interval))
                else:
                    # could not communicate with the api stoping
                    logger.info("lost connection to api server, quitting")
                    break
        except Exception as error:
            logger.warn(error)
        finally:
            self.stop()

    def __start(self):
        self.__schedule()
        self.__event_observer.start()

    def __stop(self):
        self.__event_observer.stop()
        self.__event_observer.join()

    def __schedule(self):
        self.__event_observer.schedule(
            self.__event_handler, self.__src_path, recursive=True
        )


if __name__ == "__main__":
    pass
