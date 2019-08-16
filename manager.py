import os
import sys
import time

import cloudpickle
import redis
import lz4.frame
import pandas as pd
from tqdm.auto import tqdm

# functions to pickle and unpickle (to/from string) with lz4 compression
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
        
    def get_worker_info(self):
        df = pd.DataFrame(self.r.client_list()).query("flags!='N'")[["addr","name","age","id","idle"]]
        df = df[df["name"].str.startswith(self.user)]
        return df
    
    def local_map(self, func, vargs,progress_bar=True):
        results = []
        if progress_bar:
            bar = tqdm(vargs)
        else:
            bar = vargs
        for args in bar:
            results.append(func(args))
        return results

    def clear_queues(self):
        self.r.delete(self.qname_results,self.qname_tasks)

    def remote_map(self, func, vargs, return_metadata=True):
        self.clear_queues()
        
        vals = [compress_and_dumps([func,args]) for args in vargs]
        self.r.lpush(self.qname_tasks,*vals)

        # Read results from broker
        results = []
#         bar = tqdm(total=total_nevents,unit_scale=True,unit="event")
        bar = tqdm(total=len(vargs))
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
        return results

