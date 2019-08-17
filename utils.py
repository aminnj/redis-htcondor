import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def plot_timeflow(results,ax=None):
    """
    Takes `results` returned by `remote_map`, 
    which is a list of pairs, the second elements of which are
    dicts that contain a `tstart` and `tstop` key
    as well as a `worker_name` identifier.
    """
    data = []
    for worker,df in pd.DataFrame([result[1] for result in results]).sort_values("worker_name").groupby("worker_name"):
        starts = df.tstart.values
        stops = df.tstop.values
        pairs = sorted(list(zip(starts,stops)))
        for p in pairs:
            data.append([worker,p[0],p[1]])
    df = pd.DataFrame(data,columns=["worker_name","tstart","tstop"])
    df["worker_name"] = df["worker_name"].astype("category")
    first = df["tstart"].min()
    df["tstart"] -= first
    df["tstop"] -= first
    height = 3
    if df["worker_name"].nunique() > 30: height = 5
    if df["worker_name"].nunique() >= 100: height = 9
    if df["worker_name"].nunique() >= 200: height = 15
    if ax is None:
        fig,ax = plt.subplots(figsize=(15,height))
    ax.barh(df["worker_name"].cat.codes, df["tstop"]-df["tstart"], left=df["tstart"],height=1.0,edgecolor="k",fc="C0")
    ax.set_xlabel("elapsed time since start [s]",fontsize="x-large")
    ax.set_ylabel("worker number",fontsize="x-large")
    return fig,ax

def plot_cumulative_read(results,ax=None):
    """
    Same inputs as `plot_timeflow`
    """
    df = pd.DataFrame([result[1] for result in results])
    df["elapsed"] = df["tstop"]-df["tstart"]
    df[["tstart","tstop"]] -= df["tstart"].min()
    df = df.sort_values("tstop")
    if ax is None:
        fig,ax = plt.subplots()
    xs, ys = df["tstop"],df["read_bytes"].cumsum()/1e9
    # fit a line, then fit again to only those with resids < 1sigma
    m,b = np.polyfit(xs,ys,1)
    resids = (m*xs+b)-ys
    central = (np.abs(resids-resids.mean())/resids.std() < 1.0)
    m,b = np.polyfit(xs[central],ys[central],1)
    ax.plot(xs,ys)
    ax.plot(xs,m*xs+b,label="fit ({:.2f}GB/s)".format(m))
    ax.set_xlabel("time since start [s]")
    ax.set_ylabel("cumulative read GB")
    ax.set_title("Read {:.2f}GB in {:.2f}s @ {:.3f}GB/s".format(ys.max(),xs.max(),ys.max()/xs.max()))
    ax.legend()
    return fig,ax
