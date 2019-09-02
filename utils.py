import cloudpickle
import lz4.frame
import functools
import inspect
import concurrent.futures

def compress_and_dumps(obj):
    return lz4.frame.compress(cloudpickle.dumps(obj), compression_level=lz4.frame.COMPRESSIONLEVEL_MINHC)


def decompress_and_loads(obj):
    return cloudpickle.loads(lz4.frame.decompress(obj))

def run_one_worker(args):
    import worker
    from config import REDIS_URL
    w = worker.Worker(REDIS_URL, verbose=False)
    w.start_pubsub()
    w.run()

def start_local_workers(n):
    executor = concurrent.futures.ProcessPoolExecutor(n)
    worker_futures = [executor.submit(run_one_worker, i) for i in range(n)]
    return executor, worker_futures


@functools.lru_cache(maxsize=256)
def get_chunking(filelist, chunksize, treename="Events", workers=12, skip_bad_files=False):
    """
    Return 2-tuple of
    - chunks: triplets of (filename,entrystart,entrystop) calculated with input `chunksize` and `filelist`
    - total_nevents: total event count over `filelist`
    """
    import uproot
    from tqdm.auto import tqdm
    chunks = []
    nevents = 0
    if skip_bad_files:
        # slightly slower (serial loop), but can skip bad files
        for fname in tqdm(filelist):
            try:
                items = uproot.numentries(fname, treename, total=False).items()
            except (IndexError, ValueError) as e:
                print("Skipping bad file", fname)
                continue
            for fn, nentries in items:
                nevents += nentries
                for index in range(nentries // chunksize + 1):
                    chunks.append((fn, chunksize*index, min(chunksize*(index+1), nentries)))
    else:
        executor = None if len(filelist) < 5 else concurrent.futures.ThreadPoolExecutor(min(workers, len(filelist)))
        for fn, nentries in uproot.numentries(filelist, treename, total=False, executor=executor).items():
            nevents += nentries
            for index in range(nentries // chunksize + 1):
                chunks.append((fn, chunksize*index, min(chunksize*(index+1), nentries)))
    return chunks, nevents
