import sys
import cloudpickle
import redis
import lz4.frame
import subprocess
import os
import argparse
import time

def get_classad(classad):
    stat,out = subprocess.getstatusoutput(r"""grep -i "^{}\b" "$_CONDOR_JOB_AD" | cut -d= -f2- | xargs echo""".format(classad))
    return out

def compress_and_dumps(obj):
    return lz4.frame.compress(cloudpickle.dumps(obj),compression_level=lz4.frame.COMPRESSIONLEVEL_MINHC)

def decompress_and_loads(obj):
    return cloudpickle.loads(lz4.frame.decompress(obj))

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="redis url. e.g., redis://[:password]@localhost:6379/0")
    args = parser.parse_args()

    hostname = os.uname()[1]
    try:
        taskname = str(get_classad("taskname"))
        clusterid = int(get_classad("ClusterId").split(".")[0])
        procid = int(get_classad("ProcId"))
        user = str(get_classad("User").split("@")[0]).strip()
    except:
        taskname = "local"
        clusterid = 0
        procid = 0
        user = "unknown"

    # sys.exit()

    print("url:",args.url)
    # r = redis.Redis(host=args.url)
    r = redis.Redis.from_url(args.url)
    client_name = "{}__{}__{}__{}.{}".format(user,hostname,taskname,clusterid,procid)
    print(client_name)
    r.client_setname(client_name)

    print("client_name:",client_name)

    while True:
        key,task_raw = r.brpop(user+":tasks")

        f,args = decompress_and_loads(task_raw)

        t0 = time.time()
        res = f(args)
        t1 = time.time()
        # print(key,f,args,res)
        print(key,f,args)

        meta = dict(client_name=client_name,args=args,elapsed=t1-t0)

        r.lpush(user+":results",compress_and_dumps([meta,res]))


