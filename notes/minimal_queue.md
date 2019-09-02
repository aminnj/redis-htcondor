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

r = redis.Redis.from_url("redis://localhost:6379")

while True:
    _,raw = r.brpop("tasks")
    f,args = cloudpickle.loads(raw)
    res = f(args)
    r.lpush("results",cloudpickle.dumps(res))
```

A very simple `main.py` to be run in another terminal:
```python
import time
import cloudpickle
import redis

r = redis.Redis.from_url("redis://localhost:6379")

def remote_map(func, vargs):
    vals = [cloudpickle.dumps([func,args]) for args in vargs]
    r.lpush("tasks",*vals)
    results = []
    while len(results) < len(vargs):
        _, raw = r.brpop("results")
        results.append(cloudpickle.loads(raw))
    return results

def f(x):
    time.sleep(1.0)
    return x+1
results = remote_map(f,range(5))
print(results)
```


