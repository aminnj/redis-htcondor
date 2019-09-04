import argparse
import inspect
import os
import random
import subprocess
import sys
import time
import traceback

import redis
import psutil

from utils import (compress_and_dumps, 
                   decompress_and_loads)


def get_classads():
    fname = os.getenv("_CONDOR_JOB_AD")
    if not fname:
        return {}
    d = {}
    with open(fname) as fh:
        for line in fh:
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip().lstrip('"').strip('"')
    return d

class Worker(object):
    def __init__(self, redis_url, worker_name=None, verbose=True):
        self.r = redis.Redis.from_url(redis_url)
        self.hostname = os.uname()[1]
        self.verbose = verbose

        try:
            self.classads = get_classads()
            self.clusterid = int(self.classads["ClusterId"])
            self.procid = int(self.classads["ProcId"])
            self.user = self.classads["User"].split("@")[0].strip()
        except:
            self.clusterid = 0
            self.procid = os.getpid()
            self.user = os.getenv("USER")

        self.worker_name = worker_name if worker_name else "{}__{}__{}.{}".format(
            self.user,
            self.hostname,
            self.clusterid,
            self.procid
        )
        self.r.client_setname(self.worker_name)

        self.worker_meta = dict(
            worker_name=self.worker_name,
            total_tasks=0,
            total_read_bytes=0,
            total_write_bytes=0,
            total_time_elapsed=0,
        )
        self.pubsub_thread = None
        if self.verbose:
            print("Initialized", str(self))

    def __repr__(self):
        return "<Worker {}>".format(self.worker_name)

    def start_pubsub(self):
        # Non-blocking background pubsub thread
        self.pubsub = self.r.pubsub(ignore_subscribe_messages=True)

        def handler(x):
            if x["type"] != "message":
                return
            f = decompress_and_loads(x["data"])
            try:
                f.__globals__["get_worker"] = lambda: self
                res = f()
            except:
                res = traceback.format_exc()
            self.r.lpush(self.user+":pubsubout", compress_and_dumps(res))
        self.pubsub.subscribe(**{self.user+":pubsubin": handler})
        self.pubsub_thread = self.pubsub.run_in_thread(sleep_time=0.1, daemon=True)
        return self.pubsub


    def run(self):
        # Blocking
        p = psutil.Process()
        while True:
            # listen to the general queue and also a queue especially for this worker
            try:
                key, task_raw = self.r.brpop(
                    [self.user+":tasks", self.worker_name+":tasks"])
            except ConnectionError as e:
                print("Connection error, exiting quietly.")
                break

            self.worker_meta["busy"] = True

            task_id, job_num, f, args = decompress_and_loads(task_raw)

            if self.verbose:
                print("Received task_id={}, job_num={}".format(task_id,job_num))

            try:
                ioc = p.io_counters()
                read_bytes0 = ioc.read_bytes
                write_bytes0 = ioc.write_bytes
            except AttributeError:
                # MacOS doesn't have io_counters
                pass

            t0 = time.time()
            try:
                f.__globals__["get_worker"] = lambda: self
                res = f(args)
            except Exception as e:
                res = traceback.format_exc()
            t1 = time.time()

            try:
                ioc = p.io_counters()
                read_bytes = ioc.read_bytes-read_bytes0
                write_bytes = ioc.write_bytes-write_bytes0
            except AttributeError:
                read_bytes = 0
                write_bytes = 0

            meta = dict(
                task_id=task_id,
                job_num=job_num,
                worker_name=self.worker_name,
                args=args,
                tstart=t0,
                tstop=t1,
                read_bytes=read_bytes,
                write_bytes=write_bytes,
                result=res,
            )
            payload = compress_and_dumps(meta)

            # regardless of the incoming queue, push into general results queue
            qname = self.user+":results:"+task_id
            self.r.lpush(qname, payload)

            if self.verbose:
                print("Pushed task_id={}, job_num={} to queue {}".format(task_id, job_num, qname))

            # if we got the poison pill, stop after lpush for at least some acknowledgment
            if args == "STOP":
                if self.verbose:
                    print("Stopping", str(self))
                break

            # update some total metrics about this worker
            self.worker_meta["total_read_bytes"] += read_bytes
            self.worker_meta["total_write_bytes"] += write_bytes
            self.worker_meta["total_tasks"] += 1
            self.worker_meta["total_time_elapsed"] += t1-t0

            self.worker_meta["busy"] = False


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "url", help="redis url. e.g., redis://[:password]@localhost:6379")
    args = parser.parse_args()

    w = Worker(args.url)

    w.cache = None
    try:
        import uproot
        ARRAY_CACHE = uproot.ArrayCache("8 GB")
        w.cache = ARRAY_CACHE
    except ImportError as e:
        print(e, "so we can't make a global ArrayCache")
    except AttributeError as e:
        print(e, " Maybe this is an older version of uproot without ArrayCache?")

    w.start_pubsub()
    w.run()
