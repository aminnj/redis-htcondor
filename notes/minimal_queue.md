## Minimal work-queue example

Removing all abstractions and fanciness, a minimal example of a
task queue might look like the following two files. In the main script, we put
functions and arguments into a tasks queue, which a worker will
poll and work on. The worker puts the output into the results queue,
which the main script reads from and returns to the user. Workers
don't/can't talk to each other.


A very simple `worker.py` to be run in one terminal:
```python
import cloudpickle
import redis
import traceback

if __name__ == "__main__":

    r = redis.Redis.from_url("redis://localhost:6379")

    while True:
        _,raw = r.brpop("tasks")
        f,args = cloudpickle.loads(raw)
        try: res = f(args)
        except: res = traceback.format_exc()
        r.lpush("results",cloudpickle.dumps(res))
```

A very simple `main.py` to be run in another terminal:
```python
import time
import random
import cloudpickle
import redis

class Manager(object):
    def __init__(self,redis_url):
        self.redis_url = redis_url
        self.r = redis.Redis.from_url(redis_url)
        self.qname_results = "results"
        self.qname_tasks = "tasks"

    def remote_map(self, func, vargs):
        # Serialize function, args, and push all of them to the tasks queue
        vals = [cloudpickle.dumps([func,args]) for args in vargs]
        self.r.lpush(self.qname_tasks,*vals)

        results = []
        while len(results) < len(vargs):
            _, raw = self.r.brpop(self.qname_results)
            results.append(cloudpickle.loads(raw))
        return results

if __name__ == "__main__":
    m = Manager("redis://localhost:6379")

    def f(x):
        time.sleep(random.random()*2)
        return x+1
    results = m.remote_map(f,range(5))
    print(results)
```


