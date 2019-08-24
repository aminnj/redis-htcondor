## Minimal work-queue example

Removing all abstractions and fanciness, a minimal example of a
task queue might look like the following two files. In the main script, we put
functions and arguments into a tasks queue, which a worker will
poll and work on. The worker puts the output into the results queue,
which the main script reads from and returns to the user.


A very simple `worker.py` to be run in one terminal:
```python
import os
import cloudpickle
import redis
import traceback

if __name__ == "__main__":

    url = "redis://localhost:50010"
    r = redis.Redis.from_url(url)
    user = os.getenv("USER")

    while True:
        key,task_raw = r.brpop(user+":tasks")
        f,args = cloudpickle.loads(task_raw)
        try: res = f(args)
        except: res = traceback.format_exc()
        r.lpush(user+":results",cloudpickle.dumps(res))
```


A very simple `main.py` to be run in another terminal:
```python
import os
import sys
import time
import random
import cloudpickle
import redis
from tqdm.auto import tqdm

class Manager(object):
    def __init__(self,redis_url,qname_results=None,qname_tasks=None,):
        self.redis_url = redis_url
        self.r = redis.Redis.from_url(redis_url)
        self.user = os.getenv("USER")
        self.qname_results = qname_results if qname_results else self.user+":results"
        self.qname_tasks = qname_tasks if qname_tasks else self.user+":tasks"

    def remote_map(self, func, vargs):
        # flush pre-existing stuff in the queue
        self.r.delete(self.qname_results,self.qname_tasks)

        # Serialize function, args, and push all of them to the tasks queue
        vals = [cloudpickle.dumps([func,args]) for args in vargs]
        self.r.lpush(self.qname_tasks,*vals)

        # Poll the length of the results queue
        # and read, being careful to sleep half a second
        # when polls come back empty over and over again
        # or else we spam brpops
        results = []
        bar = tqdm(total=len(vargs))
        while len(results) < len(vargs):
            tofetch = self.r.llen(self.qname_results)
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
                res = cloudpickle.loads(res_raw)
                results.append(res)
                bar.update(1)
        bar.close()
        return results

if __name__ == "__main__":
    url = "redis://localhost:50010"
    m = Manager(url)

    def f(x):
        time.sleep(random.random()*2)
        return x+1
    results = m.remote_map(f,range(5))
    print(results)
```


