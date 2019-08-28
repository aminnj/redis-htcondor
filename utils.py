import cloudpickle
import lz4.frame
import functools
import inspect
import concurrent.futures

def compress_and_dumps(obj):
    return lz4.frame.compress(cloudpickle.dumps(obj), compression_level=lz4.frame.COMPRESSIONLEVEL_MINHC)


def decompress_and_loads(obj):
    return cloudpickle.loads(lz4.frame.decompress(obj))

def get_function_kwargs(func):
    # https://stackoverflow.com/questions/2088056/get-kwargs-inside-function
    spec = inspect.getfullargspec(func)
    if spec.defaults:
        return dict(zip(spec.args[::-1], spec.defaults[::-1]))
    elif spec.kwonlyargs:
        return spec.kwonlydefaults
    else:
        return {}

# def get_redis_url():
#     try:
#         from config import REDIS_URL
#         return REDIS_URL
#     except ImportError as e:
#         raise Exception("You didn't specify a redis url, and I couldn't find one in config.REDIS_URL")
#     return None


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
