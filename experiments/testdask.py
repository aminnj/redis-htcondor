import glob
import uproot
import numpy as np
import uproot_methods

import utils
from tqdm.auto import tqdm
import time

import pandas as pd

from dask.distributed import Client
from dask.distributed import get_worker

c = Client("BLAH")
print(c)

def f(x):
    return x**2
futures = c.map(f,range(100))
results = c.gather(futures)
print(results)

fnames = sorted(glob.glob("/hadoop/cms/store/group/snt/nanoaod/DoubleMuon__Run*/*.root"))[:500]
chunks, total_nevents = utils.get_chunking(tuple(fnames),int(1.0e6))
print("{} chunks of {} files, with a total of {:.5g} events".format(len(chunks),len(fnames),total_nevents))


trial = "try8_nf500_nw100"

def get_mll_hist(args,cache=None):
    fname,entrystart,entrystop = args
    f = uproot.open(fname)
    t = f["Events"]
    try:
        cache = get_worker().array_cache
    except:
        pass
    extra = dict(outputtype=tuple,namedecode="ascii",entrystart=entrystart,entrystop=entrystop,cache=cache)
    mus = uproot_methods.TLorentzVectorArray.from_ptetaphim(
        *t.arrays(["Muon_pt","Muon_eta","Muon_phi","Muon_mass"],**extra)
    )
    mus = mus[mus.counts==2]
    mll = (mus[:,0]+mus[:,1]).mass
    bins = np.logspace(np.log10(0.5),np.log10(1000),num=300)
    counts,_ = np.histogram(np.clip(mll,bins[0],bins[-1]),bins=bins)
    return counts


# clear array_cache
workers = list(c.scheduler_info()["workers"].keys())
c.gather(c.map(lambda x: get_worker().array_cache.clear(),workers,workers=workers))

# start
c.get_task_stream()
# print(get_mll_hist(chunks[0]))
t0 = time.time()
futures = c.map(get_mll_hist,chunks)
results = c.gather(futures)
t1 = time.time()
print(len(results),"results")
print(t1-t0)
task_stream = c.get_task_stream(start=t0,stop=t1)
print("task_stream length",len(task_stream))
pd.DataFrame(task_stream).drop("type",axis=1).to_json("data/dask_cold_{}.json".format(trial))

d = c.who_has(futures)
# chunk_workers = list(zip(chunks,[d[f.key] for f in futures]))
workers = [d[f.key][0] for f in futures]
print(workers)

c.get_task_stream()
t0 = time.time()
# pure=False to avoid caching of the *results*
futures = [c.submit(get_mll_hist,chunk,pure=False,workers=worker,allow_other_workers=True) for chunk,worker in zip(chunks,workers)]
# futures = c.map(get_mll_hist,chunks,workers=workers,pure=False)
results = c.gather(futures)
t1 = time.time()
print(len(results),"results")
print(t1-t0)
task_stream = c.get_task_stream(start=t0,stop=t1)
print("task_stream length",len(task_stream))
pd.DataFrame(task_stream).drop("type",axis=1).to_json("data/dask_warm_{}.json".format(trial))

meta = zip(chunks,[f.key for f in futures])
pd.DataFrame(meta,columns=["chunk","name"]).to_json("data/dask_meta_{}.json".format(trial))
