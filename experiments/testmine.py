import glob
import uproot
import numpy as np
import uproot_methods

import utils
import manager

from tqdm.auto import tqdm
import time

import pandas as pd


# from dask.distributed import Client
# from dask.distributed import get_worker

m = manager.Manager()
print(m.get_worker_info())

def f(x):
    return x**2
results = m.remote_map(f,range(100))
print(results)

fnames = sorted(glob.glob("/hadoop/cms/store/group/snt/nanoaod/DoubleMuon__Run*/*.root"))[:500]
chunks, total_nevents = utils.get_chunking(tuple(fnames),int(1.0e6))
print("{} chunks of {} files, with a total of {:.5g} events".format(len(chunks),len(fnames),total_nevents))


trial = "try6_nf500_nw100"

def get_mll_hist(args,cache=None):
    fname,entrystart,entrystop = args
    f = uproot.open(fname)
    t = f["Events"]
    # try:
    #     cache = get_worker().array_cache
    # except:
    #     pass
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
def f(x,cache=None):
    cache.clear()
results = m.remote_map(f,m.get_worker_info().index)
print(results)

t0 = time.time()
results = m.remote_map(get_mll_hist,chunks,return_metadata=True,reuse_chunking=True)
t1 = time.time()
print(len(results),"results")
print(t1-t0)
pd.DataFrame(results).drop("result",axis=1).to_json("data/mine_cold_{}.json".format(trial))

t0 = time.time()
results = m.remote_map(get_mll_hist,chunks,return_metadata=True,reuse_chunking=True)
t1 = time.time()
print(len(results),"results")
print(t1-t0)
pd.DataFrame(results).drop("result",axis=1).to_json("data/mine_warm_{}.json".format(trial))

pd.DataFrame(chunks).to_json("data/mine_chunks_{}.json".format(trial))
