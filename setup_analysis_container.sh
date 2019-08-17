#!/usr/bin/env bash

[ -d virtualenv ] || pip install --target=`pwd`/virtualenv virtualenv
export PYTHONPATH=$PYTHONPATH:`pwd`/virtualenv
[ -d myenv ] || virtualenv/bin/virtualenv -p `which python3` myenv
source myenv/bin/activate
pip3 install matplotlib uproot coffea jupyter tqdm pandas lz4 cloudpickle redis
export LC_ALL=C.UTF-8
jupyter notebook --no-browser --port=8895
