## Todo
* Consider using [AWS](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/nodes-connecting.html) for redis broker
* Report metadata about hostname/clusterID/procID when returning a result so we know which ones are slow

## Install and deploy redis

Download and compile redis, then start it up
with appropriate handling of port forwarding.
```
curl -O -L http://download.redis.io/releases/redis-5.0.5.tar.gz
tar xf redis-5.0.5.tar.gz
cd redis-5.0.5
make

# configure pw so we can use redis outside localhost, on a given port
echo "requirepass mypass" > myconf.conf
echo "port 50013" >> myconf.conf
echo "loglevel verbose" >> myconf.conf

# launch it
./src/redis-server myconf.conf

```

In cases where redis is not bound to a public-facing port, you may have to use `ngrok`
to bind your local port (50013) in this case to something ngrok will give you.
(note that the free `ngrok` shouldn't/can't be used with more than 4 connections, so use it for testing only)
Download an unzip `ngrok` from [here](https://ngrok.com/download). Then do
```bash
./ngrok tcp 50013
```
and you'll see the public-facing port (e.g., `tcp://0.tcp.ngrok.io:16890`)

Now check to make sure the redis server is visible from another host, replacing the ngrok link if
that step is not needed/applicable
```
nc -z -v -w5 0.tcp.ngrok.io 16890
```

## Prepare environment for workers

Clone this repository and `cd` in.
```
git clone <whatever I end up calling this repo>
cd $_
```

Make a virtualenv inside the same singularity container specified in the submit file and then tarball it.
This will provide the workers with the same versions of `cloudpickle`, `python`, etc.
```
singularity shell --bind /hadoop /cvmfs/singularity.opensciencegrid.org/efajardo/docker-cms\:tensorflow 
[ -d virtualenv ] ||  pip3 install virtualenv --target=`pwd`/virtualenv virtualenv
[ -d workerenv ] || python3 virtualenv/virtualenv.py workerenv
. workerenv/bin/activate
pip3 install redis cloudpickle lz4 uproot psutil
tar cJf workerenv.tar.xz workerenv/
```


## Submit some workers

Exit the previous singularity container with <kbd>ctrl-d</kbd>.

Submit 1 or 2 workers first. If they're running for longer than 30 seconds without crashing, then
do the next step and see if the workers become visible in the notebook before going crazy launching more.
```
mkdir -p logs/
# except with the correct url and password (ask around for this)
condor_submit submit.cmd -append 'arguments="redis://:mypass@ec2-54-153-82-98.us-west-1.compute.amazonaws.com:6379"' -append 'queue 3'
# or if you used ngrok
# condor_submit submit.cmd -append 'arguments="redis://:mypass@0.tcp.ngrok.io:16890"' -append 'queue 3'
```

## Now on to doing some analysis in a jupyter notebook

Make a separate virtualenv inside the same singularity container
```
# before executing this,
# possibly edit the port in `setup_analysis_container.sh` to avoid clashes with other users
./start_analysis_server.sh

# visit the url printed out at the end and make sure to forward the port to your laptop first. e.g.,
ssh -N -f -L localhost:8895:localhost:8895 uaf-10.t2.ucsd.edu
```

Open `example.ipynb` and play around.
