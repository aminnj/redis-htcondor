def dask_setup(worker):
    import os

    def get_classads():
        fname = os.getenv("_CONDOR_JOB_AD")
        if not fname:
            return {}
        d = {}
        with open(fname) as fh:
            for line in fh:
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip().lstrip('"').strip('"')
        return d

    worker.array_cache = None
    try:
        import uproot
        worker.array_cache = uproot.ArrayCache("8 GB")
    except ImportError as e:
        print(e, "so we can't make a global ArrayCache")
    except AttributeError as e:
        print(e, " Maybe this is an older version of uproot without ArrayCache?")

    worker.classads = get_classads()
