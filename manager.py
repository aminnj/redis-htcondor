import os
import sys
import time
import random
import uuid
from collections import defaultdict

import cloudpickle
import redis
import lz4.frame
import pandas as pd
from tqdm.auto import tqdm

from utils import (compress_and_dumps, 
                   decompress_and_loads)

class Manager(object):
    def __init__(self, redis_url=None, qname_results=None, qname_tasks=None):
        if not redis_url:
            try:
                from config import REDIS_URL
                redis_url = REDIS_URL
            except ImportError as e:
                raise Exception(
                    "You didn't specify a redis url, and I couldn't find one in config.REDIS_URL")
        self.redis_url = redis_url
        self.r = redis.Redis.from_url(redis_url)
        self.user = os.getenv("USER")
        self.qname_results = qname_results if qname_results else self.user+":results"
        self.qname_tasks = qname_tasks if qname_tasks else self.user+":tasks"
        self.remote_results = []

    def __repr__(self):
        def valid(x):
            return (x["flags"]!="N") and (x["name"].startswith(self.user))
        return "<Manager: broker='{}', workers={}>".format(
                self.redis_url,
                sum(map(valid,self.r.client_list())),
                )

    def get_worker_info(self, include_stats=False, stat_integration_time=2.0):
        def valid(x):
            return (x["flags"]!="N") and (x["name"].startswith(self.user))
        df = pd.DataFrame([c for c in self.r.client_list() if valid(c)])
        if df.empty: return pd.DataFrame()
        df = df[["addr", "name", "age", "id", "idle"]]
        if not include_stats:
            return df.set_index("name")

        def f(meta):
            import psutil
            p = psutil.Process()
            t1 = time.time()
            net1 = psutil.net_io_counters()
            disk1 = psutil.disk_io_counters()
            time.sleep(stat_integration_time)
            t2 = time.time()
            net2 = psutil.net_io_counters()
            disk2 = psutil.disk_io_counters()
            return dict(
                meta=meta,
                t1=t1, t2=t2,
                net1=net1, net2=net2,
                disk1=disk1, disk2=disk2,
                mem_used=p.memory_info()[0],
            )
        self.r.publish(self.user+":channel1", compress_and_dumps(f))
        # wait 1 more second than the process should've slept and fetch results in one shot
        time.sleep(stat_integration_time+1.)
        pipe = self.r.pipeline()
        pipe.lrange(self.user+":channel1results", 0, -1)
        pipe.delete(self.user+":channel1results")
        results = pipe.execute()[0]

        def f(x):
            d = decompress_and_loads(x)
            ret = {}
            try:
                ret["name"] = d["meta"]["worker_name"]
                ret["worker_time_elapsed"] = d["meta"]["total_time_elapsed"]
                ret["worker_write_bytes"] = d["meta"]["total_write_bytes"]
                ret["worker_read_bytes"] = d["meta"]["total_read_bytes"]
                ret["worker_tasks"] = d["meta"]["total_tasks"]
                ret["worker_mem_used"] = d["mem_used"]
                ret["node_dt"] = d["t2"]-d["t1"]
                ret["node_read_bytes"] = d["disk2"].read_bytes - \
                    d["disk1"].read_bytes
                ret["node_write_bytes"] = d["disk2"].write_bytes - \
                    d["disk1"].write_bytes
                ret["node_recv_bytes"] = d["net2"].bytes_recv - \
                    d["net1"].bytes_recv
                ret["node_sent_bytes"] = d["net2"].bytes_sent - \
                    d["net1"].bytes_sent
            except:
                pass
            return ret
        df["node"] = df["name"].str.split("__").str[1]
        df = df.merge(pd.DataFrame(map(f, results)),
                      on="name", how="outer").set_index("name")
        failed = df["node_dt"].isna().sum()
        if failed > 0:
            print("Did not hear back from {} workers in time".format(failed))
        return df

    def get_broker_info(self):
        return self.r.info("all")

    def local_map(self, func, vargs, progress_bar=True):
        return list(map(func, tqdm(vargs, disable=not progress_bar)))

    def clear_queues(self):
        self.r.delete(self.qname_tasks)

    def stop_all_workers(self, **kwargs):
        return self.remote_map(lambda x: x, ["STOP"]*len(self.get_worker_info()), **kwargs)

    def remote_map(self, func, vargs, return_metadata=True,
                   reuse_chunking=False, worker_names=[],
                   shuffle_chunks=False,
                   skip_payload_check=False,
                   blocking=True,
                   progress_bar=True,
                   ):

        # If user tries to send more than 2MB (compressed) to each worker, stop them!
        if not skip_payload_check and len(vargs):
            compressed_size_mb = len(compress_and_dumps([func, vargs[0]]))/1e6
            if compressed_size_mb > 2:
                raise RuntimeError(
                    "You're trying to send {:.1f}MB (more than 2MB) through the server. "
                    "This will slow things down. Please check your function and arguments.".format(
                        compressed_size_mb)
                )

        # Remove leftover/errored tasks
        self.clear_queues()

        vargs, worker_names = self.optimize_chunking(
            vargs, worker_names, reuse_chunking=reuse_chunking, shuffle_chunks=shuffle_chunks)
        task_id = uuid.uuid4().hex[:16] # 32 bytes to keep it short and simple
        vals = [compress_and_dumps([task_id, func, args]) for args in vargs]

        # If user specified enough worker names to cover all tasks we will submit,
        # then submit them to those workers specifically, otherwise
        # submit to the general task queue
        if len(worker_names) >= len(vals):
            pipe = self.r.pipeline()
            for worker_name, val in zip(worker_names, vals):
                self.r.lpush("{}:tasks".format(worker_name), val)
            pipe.execute()
        else:
            self.r.lpush(self.qname_tasks, *vals)

        qname_results_tid = self.qname_results+":"+task_id

        def results_generator(self):
            # Read results from broker
            results = []
            ntasks = len(vargs)
            # , unit_scale=True,unit="event")
            bar = tqdm(total=len(vargs), disable=(not progress_bar or not blocking))
            npolls = 0
            while len(results) < ntasks:
                tofetch = self.r.llen(qname_results_tid)
                # avoid spamming pops requests too fast
                if tofetch == 0:
                    if npolls < 5:
                        time.sleep(0.005*npolls**2)
                    else:
                        time.sleep(0.5)
                    npolls += 1
                    continue
                pipe = self.r.pipeline()
                pipe.lrange(qname_results_tid, 0, -1)
                pipe.delete(qname_results_tid)
                popchunk = pipe.execute()[0]
                for pc in popchunk[::-1]:
                    if pc is None:
                        continue
                    res = decompress_and_loads(pc)
                    if not return_metadata:
                        res = res["result"]
                    results.append(res)
                    yield res
                    bar.update(1)
            bar.close()
            self.remote_results = results

        if blocking:
            return list(results_generator(self))
        else:
            return results_generator(self)

    def optimize_chunking(self, vargs, worker_names, reuse_chunking=False, shuffle_chunks=False):
        # If the previous chunking matches the current chunking, then
        # use the old chunks and corresponding worker names to make use of
        # cached branches
        if reuse_chunking and self.remote_results and (type(self.remote_results[0]) == dict):
            old_vargs = [r["args"] for r in self.remote_results]
            old_worker_names = [r["worker_name"] for r in self.remote_results]
            if (type(vargs[0]) in [tuple, list]) and (sorted(map(tuple, vargs)) == sorted(map(tuple, old_vargs))):
                vargs = old_vargs
                worker_names = old_worker_names
                print("Current chunking matches old chunking, so we will re-use the old worker ordering "
                      "to make use of caching")

        # Ability to shuffle chunks in case consecutive jobs land on the same disk and compete
        if shuffle_chunks:
            if len(worker_names) >= len(vargs):
                combined = list(zip(vargs, worker_names))
                random.shuffle(combined)
                vargs, worker_names = zip(*combined)
            else:
                random.shuffle(vargs)

        return vargs, worker_names
