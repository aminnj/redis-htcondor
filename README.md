## Introduction

### Motivation

The specific goal of this repository is to analyze CMS NanoAOD ROOT files with [uproot](https://github.com/scikit-hep/uproot)
in a similar style to [coffea](https://github.com/CoffeaTeam/coffea), but using a master/manager
that sends computing tasks to workers running in an HTCondor batch system.

There are a handful of tools designed to do this more generally (dynamic task execution with brokered communication):
[htmap](https://github.com/htcondor/htmap),
[parsl](https://github.com/Parsl/parsl),
[dask](https://distributed.dask.org/en/latest/),
[celery](https://github.com/celery/celery),
[ray](https://github.com/ray-project/ray),
[airflow](https://github.com/apache/airflow),
[dramatiq](https://github.com/Bogdanp/dramatiq)
.

Unfortunately, limitations on what ports are open/how processes communicate
within and outside the batch system means it would be difficult to use these
out of the box. So here I have a simple task queue system that allows me to
have more low-level customization to suit ROOT file analysis (data locality,
caching, compressed communication).  The jobs are "embarrassingly parallel",
so there's no real need for complex dynamic logic, direct inter-worker
communication, DAGs, etc, and this relies on exactly one redis master server
(one single public-facing ip/port).

### Overview

I'm picking parts from the previous libraries as I go including
what's most relevant/allowed for my use case. As the base, the task system, described
in more detail [here](notes/minimal_queue.md), takes functions and arguments
from the user and serializes them with cloudpickle and compresses with lz4 
before sending these out to workers which call the functions and return the
output to the user.

TODO items are [here](notes/todo.md).


## Quick start

If someone has not already setup the redis master server, instructions
to do that are [here](notes/installing_redis.md).

While later scripts will accept a redis url to connect to, it's more convenient to specify it once,
so make a `config.py` file in the current directory containing the following line (appropriately modified)
```
REDIS_URL = "redis://:mypass@hostname:port"
```

Initial set up for workers:
```bash
# Clone this repository and `cd` in.
git clone https://github.com/aminnj/redis-htcondor
cd redis-htcondor

# Make the tarball'ed environment for the condor worker nodes.
scripts/make_worker_tarball.sh

# Submit a couple of workers initially. Ask around for the redis url.
scripts/submit_workers.py --num_workers 2
```

Launch jupyter notebook for analysis:
```bash
# Before executing, edit the port in this file to avoid clashes with other users
# who also are running jupyter notebooks on the same machine
scripts/start_analysis_server.sh

# visit the url printed out at the end and make sure to forward the port to your laptop first. e.g.,
ssh -N -f -L localhost:8895:localhost:8895 uaf-10.t2.ucsd.edu

# open `example.ipynb` and play around.
```

## Example usage

Start a local worker
```python
>>> from worker import Worker
>>> w = Worker("redis://:mypass@hostname:port")
>>> w.run() # this blocks indefinitely
```

In a separate process,
```python
>>> from manager import Manager
>>> m = Manager()
>>> results = m.remote_map(lambda x:x**2,range(10))
[0, 4, 1, 16, 25, 9, 49, 64, 81, 36]
```
