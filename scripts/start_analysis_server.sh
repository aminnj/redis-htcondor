#!/usr/bin/env bash
cat << EOF | singularity shell --bind /hadoop /cvmfs/singularity.opensciencegrid.org/efajardo/docker-cms\:tensorflow

[ -d virtualenv ] || pip install --target=$(pwd)/virtualenv virtualenv
export PYTHONPATH=$PYTHONPATH:$(pwd)/virtualenv
[ -d myenv ] || virtualenv/bin/virtualenv myenv
source myenv/bin/activate
pip3 install matplotlib uproot coffea jupyter tqdm pandas lz4 cloudpickle redis psutil
export LC_ALL=C.UTF-8
export PYTHONPATH=$(pwd):$PYTHONPATH
jupyter notebook --no-browser --port=8895

EOF

