## Experimenting with other packages

Nodes aren't visible to each other, so can't explore other things like `dask`, `ray`, ...
until they are open.

### Dask

* `pip3 install dask distributed` (worker and local)

* Before making worker tarball, edit the `workerenv/bin/dask-worker` to
have `#!/usr/bin/env python3` as the shebang line instead of the one
hardcoded when the virtualenv was set up.

* `dask-scheduler --dashboard --show` and then submit worker jobs with
`dask-worker SCHEDULERADDRESS --memory-limit 8GB --nprocs 1 --nthreads 1`
port forward the dashboard port to your laptop so you can monitor in real time.

* Works in an interactive python, but making a client hangs in jupyter (from google, is this a python 3.5 issue? https://github.com/dask/distributed/issues/2414)

* TODO
  * Try out stuff in https://examples.dask.org/applications/embarrassingly-parallel.html
  * In particular, `client.submit` (https://distributed.dask.org/en/latest/api.html?highlight=submit#distributed.Client.submit) takes a list of workers to run on

* Because of the jupyter issue mentioned above, I'm running this locally with `python test.py`
```python
import glob
import uproot
import numpy as np
import uproot_methods

import utils

from dask.distributed import Client
client = Client("tcp://BLAHBLAH")
print(client)

def f(x):
    return x**2
futures = client.map(f,range(10))
results = client.gather(futures)
print(results)

fnames = sorted(glob.glob("/hadoop/cms/store/group/snt/nanoaod/DoubleMuon__Run*/*.root"))[:10]
chunks, total_nevents = utils.get_chunking(tuple(fnames),int(1.0e6))
print("{} chunks of {} files, with a total of {:.5g} events".format(len(chunks),len(fnames),total_nevents))

def get_mll_hist(args,cache=None):
    fname,entrystart,entrystop = args
    f = uproot.open(fname)
    t = f["Events"]
    extra = dict(outputtype=tuple,namedecode="ascii",entrystart=entrystart,entrystop=entrystop,cache=cache)
    mus = uproot_methods.TLorentzVectorArray.from_ptetaphim(
        *t.arrays(["Muon_pt","Muon_eta","Muon_phi","Muon_mass"],**extra)
    )
    mus = mus[mus.counts==2]
    mll = (mus[:,0]+mus[:,1]).mass
    bins = np.logspace(np.log10(0.5),np.log10(1000),num=300)
    counts,_ = np.histogram(np.clip(mll,bins[0],bins[-1]),bins=bins)
    return counts

# print(get_mll_hist(chunks[0]))
futures = client.map(get_mll_hist,chunks)
results = client.gather(futures)
print(results)
```
  * Now what about caching? According to https://stackoverflow.com/questions/45008852/how-to-store-worker-local-variables-in-dask-distributed we could store an arraycache in the global worker state
  * Implement caching by broadcasting a function start an array cache,then submit jobs, then calculate event rate with `distributed.as_completed`. next time, map with a worker list (how to get this?)
  * Or maybe we just preload the cache? https://github.com/dask/distributed/pull/1016
    * `dask-worker tcp://169.228.130.74:8786 --memory-limit 8GB --nprocs 1 --nthreads 1 --preload blah.py`

### Ray

* `pip3 install ray` (worker and local)

* Same note as above about virtualenv shebang (except for the `ray` executable)

* Start head node: `ray start --head --redis-port=6379`

* Start workers in condor jobs with `ray start --redis-address SCHEDULERADDRESS --num-cpus 1 --num-gpus 0 --block`

