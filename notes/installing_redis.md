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

The redis url for use with `redis.Redis.from_url()` is of the form
* `redis://:mypass@ec2-54-153-82-98.us-west-1.compute.amazonaws.com:6379`
* `redis://:mypass@0.tcp.ngrok.io:16890`
