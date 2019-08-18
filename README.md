## Introduction

The specific goal of this repository is to analyze CMS NanoAOD ROOT files with [uproot](https://github.com/scikit-hep/uproot)
in a similar style to [coffea](https://github.com/CoffeaTeam/coffea) using a master/manager
that sends computing tasks to workers running in an HTCondor batch system.

There are a handful of tools designed to do this more generally (dynamic task execution with brokered communication):
* [parsl](https://github.com/Parsl/parsl)
* [dask](https://distributed.dask.org/en/latest/)
* [celery](https://github.com/celery/celery)
* [ray](https://github.com/ray-project/ray)
* [airflow](https://github.com/apache/airflow)

Unfortunately, limitations on what ports are open/how processes communicate
within and outside the batch system means it would be difficult to use these
out of the box. So here I have a simple task queue system that allows me to
have more low-level customization to suit ROOT file analysis (data locality,
caching, compressing communication).  The jobs are "embarrassingly parallel",
so there's no real need for complex dynamic logic, direct inter-worker
communication, DAGs, etc, and this relies on exactly one redis master server
(one single public-facing ip/port).

## Quick start

Initial set up for workers:
```bash
# Clone this repository and `cd` in.
git clone https://github.com/aminnj/redis-htcondor
cd redis-htcondor

# Make the tarball'ed environment for the worker nodes.
scripts/make_worker_tarball.sh

# Submit a couple of workers initially. Ask around for the redis url.
scripts/submit_workers.py redis://:mypass@hostname:port --num_workers 2
```

Launch jupyter notebook for analysis:
```bash
# Before executing, edit the port in this file to avoid clashes with other users
scripts/start_analysis_server.sh

# visit the url printed out at the end and make sure to forward the port to your laptop first. e.g.,
ssh -N -f -L localhost:8895:localhost:8895 uaf-10.t2.ucsd.edu

# open `example.ipynb` and play around.
```

## Example usage

```python
import manager
m = Manager("redis://:pass@hostname:port")
def f(x):
    return x**2
results = m.remote_map(f,range(10))
[0, 4, 1, 16, 25, 9, 49, 64, 81, 36]
```
