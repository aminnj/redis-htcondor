## Install and deploy redis

### Manually

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

### With docker (or singularity)

Redis has a docker container, so we can just use that. With Singularity, the
incantation matching the instructions from the previous section would be
```bash
singularity exec docker://redis redis-server --port $((RANDOM%1000+50000)) --requirepass mypass --loglevel verbose
# or instead of using tcp port, use a unix socket per user
singularity exec docker://redis redis-server --unixsocket /tmp/redis${USER} --loglevel verbose
```
Once it's running, we can test it from another host with netcat:
```bash
# if you included `--requirepass mypass`
(printf "AUTH mypass\nPING\n";) | nc <hostname> 12345
# otherwise
(printf "PING\n";) | nc <hostname> 12345
# if using a unix socket
(printf "PING\n";) | nc -U /tmp/redis${USER}
```
