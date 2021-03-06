import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import functools
import concurrent.futures
import uproot
from tqdm.auto import tqdm

def bokeh_output_notebook():
    from bokeh.io import output_notebook
    output_notebook()

def plot_timeflow(results, ax=None):
    """
    Takes `results` returned by `remote_map`,
    which is a list of pairs, the second elements of which are
    dicts that contain a `tstart` and `tstop` key
    as well as a `worker_name` identifier.
    """
    data = []
    dfr = pd.DataFrame(results).sort_values(["worker_name","tstart","tstop"]).groupby("worker_name")
    for worker, df in dfr:
        starts = df.tstart.values
        stops = df.tstop.values
        pairs = sorted(list(zip(starts, stops)))
        for p in pairs:
            data.append([worker, p[0], p[1]])
    df = pd.DataFrame(data, columns=["worker_name", "tstart", "tstop"])
    df["worker_name"] = df["worker_name"].astype("category")
    first = df["tstart"].min()
    df["tstart"] -= first
    df["tstop"] -= first
    height = 3
    if df["worker_name"].nunique() > 30:
        height = 5
    if df["worker_name"].nunique() >= 80:
        height = 9
    if df["worker_name"].nunique() >= 200:
        height = 15
    if ax is None:
        fig, ax = plt.subplots(figsize=(15, height))
    dt = df["tstop"]-df["tstart"]
    colors = np.array(["C0"]*len(df))
    colors[dt > dt.mean()+dt.std()*5] = "C3"
    ax.barh(df["worker_name"].cat.codes, df["tstop"]-df["tstart"],
            left=df["tstart"], height=1.0, linewidth=0.5, edgecolor="k", color=colors)
    ax.set_xlabel("elapsed time since start [s]", fontsize="x-large")
    ax.set_ylabel("worker number", fontsize="x-large")
    wtime = (df["tstop"]-df["tstart"]).sum()
    ttime = df["tstop"].max()*df["worker_name"].nunique()
    ax.set_xlim([0., df["tstop"].max()])
    ax.set_title(", ".join([
        "efficiency (filled/total) = {:.1f}%".format(100.0*wtime/ttime),
        "mean task time = {:.1f}ms".format(1e3*dfr.apply(lambda x:x["tstop"]-x["tstart"]).mean()),
        "mean intertask time = {:.1f}ms".format(1e3*dfr.apply(lambda x:x["tstart"].shift(-1)-x["tstop"]).mean()),
        ]))


def plot_cumulative_read(results, ax=None):
    """
    Same inputs as `plot_timeflow`
    """
    df = pd.DataFrame(results)
    df["elapsed"] = df["tstop"]-df["tstart"]
    df[["tstart", "tstop"]] -= df["tstart"].min()
    df = df.sort_values("tstop")
    if ax is None:
        fig, ax = plt.subplots()
    xs, ys = df["tstop"], df["read_bytes"].cumsum()/1e9
    ax.plot(xs, ys)

    # https://stackoverflow.com/questions/13691775/python-pinpointing-the-linear-part-of-a-slope
    # create convolution kernel for calculating
    # the smoothed second order derivative
    smooth_width = int(len(xs)*0.5)
    x1 = np.linspace(-3, 3, smooth_width)
    norm = np.sum(np.exp(-x1**2)) * (x1[1]-x1[0])
    y1 = (4*x1**2 - 2) * np.exp(-x1**2) / smooth_width*8
    y_conv = np.convolve(ys, y1, mode="same")
    central = (np.abs(y_conv) < y_conv.std()/2.0)
    m, b = np.polyfit(xs[central], ys[central], 1)
    # fit again with points closest to the first fit
    resids = (m*xs+b)-ys
    better = (np.abs(resids-resids.mean())/resids.std() < 1.0)
    m, b = np.polyfit(xs[better & central], ys[better & central], 1)
    ax.plot(xs[better & central], m*xs[better & central] + b,
            label="fit ({:.2f}GB/s)".format(m))
    ax.set_xlabel("time since start [s]")
    ax.set_ylabel("cumulative read GB")
    ax.set_title("Read {:.2f}GB in {:.2f}s @ {:.3f}GB/s".format(ys.max(), xs.max(), ys.max()/xs.max()))
    ax.legend()


def plot_cumulative_events(results, ax=None):
    """
    Same inputs as `plot_timeflow`
    """
    df = pd.DataFrame(results)
    try:
        df["estart"] = df["args"].str[1]
        df["estop"] = df["args"].str[2]
    except:
        return
    df["elapsed"] = df["tstop"]-df["tstart"]
    df[["tstart", "tstop"]] -= df["tstart"].min()
    df = df.sort_values("tstop")
    if ax is None:
        fig, ax = plt.subplots()
    xs, ys = df["tstop"], (df["estop"]-df["estart"]).cumsum()/1e6
    ax.plot(xs, ys)

    # https://stackoverflow.com/questions/13691775/python-pinpointing-the-linear-part-of-a-slope
    # create convolution kernel for calculating
    # the smoothed second order derivative
    smooth_width = int(len(xs)*0.5)
    x1 = np.linspace(-3, 3, smooth_width)
    norm = np.sum(np.exp(-x1**2)) * (x1[1]-x1[0])
    y1 = (4*x1**2 - 2) * np.exp(-x1**2) / smooth_width*8
    y_conv = np.convolve(ys, y1, mode="same")
    central = (np.abs(y_conv) < y_conv.std()/2.0)
    m, b = np.polyfit(xs[central], ys[central], 1)
    # fit again with points closest to the first fit
    resids = (m*xs+b)-ys
    better = (np.abs(resids-resids.mean())/resids.std() < 1.0)
    m, b = np.polyfit(xs[better & central], ys[better & central], 1)
    ax.plot(xs[better & central], m*xs[better & central] + b,
            label="fit ({:.2f}Mevents/s)".format(m))
    ax.set_xlabel("time since start [s]")
    ax.set_ylabel("cumulative Mevents")
    ax.set_title("Processed {:.2f}Mevents in {:.2f}s @ {:.3f}MHz".format(
        ys.max(), xs.max(), ys.max()/xs.max()))
    ax.legend()

def plot_timeflow_bokeh(results):
    from bokeh.io import show, output_notebook
    from bokeh.models import ColumnDataSource
    from bokeh.plotting import figure

    df = pd.DataFrame(results)[["worker_name","tstart","tstop"]].sort_values(["worker_name","tstart"])
    df[["tstart","tstop"]] -= df["tstart"].min()
    df["duration"] = df["tstop"] - df["tstart"]
    df["worker_num"] = df["worker_name"].astype("category").cat.codes.astype(str)

    if df["tstop"].max() > 10.: mult, unit = 1, "s"
    else: mult, unit = 1000, "ms"
        
    df[["tstart","tstop"]] *= mult

    group = df.groupby("worker_num")
    source = ColumnDataSource(group)

    wtime = (df["tstop"]-df["tstart"]).sum()
    ttime = df["tstop"].max()*df["worker_num"].nunique()
    title = (", ".join([
        "efficiency (filled/total) = {:.1f}%".format(100.0*wtime/ttime),
        "median task time = {:.2f}{}".format(group.apply(lambda x:x["tstop"]-x["tstart"]).median(),unit),
        "median intertask time = {:.2f}{}".format(group.apply(lambda x:x["tstart"].shift(-1)-x["tstop"]).median(),unit),
        ]))

    p = figure(y_range=group, x_range=[0,df["tstop"].max()], title=title,
               tooltips = [
                   ["worker_name","@worker_name"],
                   ["start","@{tstart}"+unit],
                   ["stop","@{tstop}"+unit],
                   ["duration","@{duration}"+unit],
               ],
              )
    p.hbar(y="worker_num", left="tstart", right="tstop", height=1.0, line_color="black", source=df)
    p.xaxis.axis_label = "elapsed time since start ({})".format(unit)
    p.yaxis.axis_label = "worker number"
    p.plot_width = 800
    p.plot_height = 350

    show(p)
