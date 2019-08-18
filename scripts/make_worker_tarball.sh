#!/usr/bin/env bash
cat << EOF | singularity shell --bind /hadoop /cvmfs/singularity.opensciencegrid.org/efajardo/docker-cms\:tensorflow

[ -d virtualenv ] ||  pip3 install virtualenv --target=$(pwd)/virtualenv virtualenv
[ -d workerenv ] || python3 virtualenv/virtualenv.py workerenv
. workerenv/bin/activate
pip3 install redis cloudpickle lz4 uproot psutil diskcache
echo "Making workerenv.tar.xz"
tar cJf workerenv.tar.xz workerenv/
echo "Done"

EOF
