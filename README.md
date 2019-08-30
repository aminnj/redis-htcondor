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
caching, compressed communication). The jobs are "embarrassingly parallel",
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

Clone the repository and work inside it:
```bash
git clone https://github.com/aminnj/redis-htcondor
cd redis-htcondor
```


Set up your own redis master server in a GNU screen on an SLC7 computer (e.g., uaf-1) with
```bash
singularity exec docker://redis redis-server --port $((RANDOM%1000+50000)) --loglevel verbose
```
(More custom installation instructions can be found [here](notes/installing_redis.md)).

While later scripts will accept a redis url to connect to, it's more convenient to specify it once,
so make a `config.py` file in the current directory containing the following line (appropriately modified
to point to the already-running server)
```
REDIS_URL = "redis://hostname:port"
```

Once the server is running, the rest can be done on an SLC6 or SLC7 computer.

Initial set up for workers:
```bash
# Make the tarballed environment for the condor worker nodes.
# This essentially tarballs a virtualenv with the minimal python
# dependencies for the worker.
scripts/make_worker_tarball.sh

# Submit a couple of workers initially
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

## Unit tests

Unit tests can be run with
```
scripts/run_tests.sh
```
after verifying that `config.py` contains the correct/running redis server url.
Arguments are passed to python call, which uses the unittest module, 
so you can run a single test with
```
scripts/run_tests.sh ManagerTest.test_local_map
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
