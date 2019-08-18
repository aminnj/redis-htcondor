import os
import sys
import time
import random
from collections import defaultdict

import cloudpickle
import redis
import lz4.frame
import pandas as pd
from tqdm.auto import tqdm

# pickle and unpickle (to/from string) with lz4 compression
# note, cloudpickle requires same python version used locally and on worker!!
# this could be relaxed with a different pickle protocol in dumps(), but then life gets messier
def compress_and_dumps(obj):
    return lz4.frame.compress(cloudpickle.dumps(obj),compression_level=lz4.frame.COMPRESSIONLEVEL_MINHC)

def decompress_and_loads(obj):
    return cloudpickle.loads(lz4.frame.decompress(obj))

class Manager(object):
    def __init__(self,redis_url,qname_results=None,qname_tasks=None,):
        self.redis_url = redis_url
        self.r = redis.Redis.from_url(redis_url)
        self.user = os.getenv("USER")
        self.qname_results = qname_results if qname_results else self.user+":results"
        self.qname_tasks = qname_tasks if qname_tasks else self.user+":tasks"
        self.remote_results = []

    def get_worker_info(self):
        df = pd.DataFrame(self.r.client_list()).query("flags!='N'")[["addr","name","age","id","idle"]]
        df = df[df["name"].str.startswith(self.user+"__")]
        return df

    def local_map(self, func, vargs,progress_bar=True):
        results = []
        bar = tqdm(vargs, disable=not progress_bar)
        for args in bar:
            results.append(func(args))
        return results

    def clear_queues(self):
        self.r.delete(self.qname_results,self.qname_tasks)

    def remote_map(self, func, vargs, return_metadata=True,
                   progress_bar=True,reuse_chunking=True,worker_names=[],
                   shuffle_chunks=False,
                  ):
        self.clear_queues()

        # If the previous chunking matches the current chunking, then
        # use the old chunks and corresponding worker names to make use of
        # cached branches
        if reuse_chunking and self.remote_results and len(self.remote_results[0]) == 2:
            old_vargs = [r[1]["args"] for r in self.remote_results]
            old_worker_names = [r[1]["worker_name"] for r in self.remote_results]
            if sorted(map(tuple,chunks)) == sorted(map(tuple,old_vargs)):
                vargs = old_vargs
                worker_names = old_worker_names
                print("Current chunking matches old chunking, so we will re-use the old worker ordering "
                      "to make use of caching")

        # Ability to shuffle chunks in case consecutive jobs land on the same disk and compete
        if shuffle_chunks:
            if len(worker_names) >= len(vargs):
                combined = list(zip(vargs,worker_names))
                random.shuffle(combined)
                vargs, worker_names = zip(*combined)
            else:
                random.shuffle(vargs)

        vals = [compress_and_dumps([func,args]) for args in vargs]

        # If user specified enough worker names to cover all tasks we will submit,
        # then submit them to those workers specifically, otherwise
        # submit to the general task queue
        if len(worker_names) >= len(vals):
            pipe = self.r.pipeline()
            for worker_name,val in zip(worker_names,vals):
                self.r.lpush("{}:tasks".format(worker_name),val)
            pipe.execute()
        else:
            self.r.lpush(self.qname_tasks,*vals)

        # Read results from broker
        results = []
        bar = tqdm(total=len(vargs), disable=not progress_bar)
        while len(results) < len(vargs):
            tofetch = self.r.llen(self.qname_results)
            # avoid spamming pops requests too fast
            if tofetch == 0:
                time.sleep(0.5)
                continue
            pipe = self.r.pipeline()
            for _ in range(tofetch):
                pipe.brpop(self.qname_results)
            popchunk = pipe.execute()
            for pc in popchunk:
                if pc is None: continue
                qname,res_raw = pc
                res = decompress_and_loads(res_raw)
                if return_metadata:
                    results.append(res)
                else:
                    results.append(res[0])
                bar.update(1)
        bar.close()
        self.remote_results = results
        return results

