import sys
import cloudpickle
import redis
import lz4.frame
import subprocess
import os
import argparse
import time
import psutil
import traceback
import random
import diskcache
import inspect

def get_classads():
    fname = os.getenv("_CONDOR_JOB_AD")
    if not fname: return {}
    d = {}
    with open(fname) as fh:
        for line in fh:
            if "=" not in line: continue
            k,v = line.split("=",1)
            d[k.strip()] = v.strip().lstrip('"').strip('"')
    return d

def compress_and_dumps(obj):
    return lz4.frame.compress(cloudpickle.dumps(obj),compression_level=lz4.frame.COMPRESSIONLEVEL_MINHC)

def decompress_and_loads(obj):
    return cloudpickle.loads(lz4.frame.decompress(obj))

def get_function_kwargs(func):
    # https://stackoverflow.com/questions/2088056/get-kwargs-inside-function
    spec = inspect.getfullargspec(func)
    if not spec.defaults: return {}
    return dict(zip(spec.args[::-1], spec.defaults[::-1]))

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="redis url. e.g., redis://[:password]@localhost:6379")
    args = parser.parse_args()

    hostname = os.uname()[1]
    try:
        classads = get_classads()
        clusterid = int(classads["ClusterId"])
        procid = int(classads["ProcId"])
        user = classads["User"].split("@")[0].strip()
    except:
        clusterid = 0
        procid = 0
        user = os.getenv("USER")

    print("url:",args.url)
    r = redis.Redis.from_url(args.url)
    worker_name = "{}__{}__{}.{}".format(user,hostname,clusterid,procid)

    r.client_setname(worker_name)

    print("worker_name:",worker_name)

    p = psutil.Process()

    try:
        import uproot
        array_cache = uproot.ArrayCache("4 GB")
    except:
        print("uproot not found, so can't make an ArrayCache")

    worker_meta = dict(
            worker_name=worker_name,
            total_tasks=0,
            total_read_bytes=0,
            total_write_bytes=0,
            total_time_elapsed=0,
            )

    # Background pubsub thread
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    def handler(x): 
        if x["type"] != "message": 
            return
        f = decompress_and_loads(x["data"])
        try:
            res = f(worker_meta)
        except:
            res = traceback.format_exc()
        r.lpush(user+":channel1results",compress_and_dumps(res))
    pubsub.subscribe(**{user+":channel1": handler})
    thread = pubsub.run_in_thread(sleep_time=0.1,daemon=True)
            
    while True:
        # listen to the general queue and also a queue especially for this worker
        key,task_raw = r.brpop([
            user+":tasks",
            worker_name+":tasks",
            ])

        f,args = decompress_and_loads(task_raw)

        ioc = p.io_counters()
        read_bytes0 = ioc.read_bytes
        write_bytes0 = ioc.write_bytes

        t0 = time.time()
        try:
            # check for `f(..., cache=None)` and fill cache kwarg
            kwargs = get_function_kwargs(f)
            if kwargs.get("cache","") is None:
                res = f(args,cache=array_cache)
            else:
                res = f(args)
        except:
            res = traceback.format_exc()
        t1 = time.time()

        ioc = p.io_counters()
        read_bytes1 = ioc.read_bytes
        write_bytes1 = ioc.write_bytes

        read_bytes = read_bytes1-read_bytes0
        write_bytes = write_bytes1-write_bytes0

        meta = dict(
            worker_name=worker_name,
            args=args,
            tstart=t0,
            tstop=t1,
            read_bytes=read_bytes,
            write_bytes=write_bytes,
            )

        worker_meta["total_read_bytes"] += read_bytes
        worker_meta["total_write_bytes"] += write_bytes
        worker_meta["total_tasks"] += 1
        worker_meta["total_time_elapsed"] += t1-t0

        # regardless of the incoming queue, push into general results queue
        r.lpush(user+":results",compress_and_dumps([res,meta]))

