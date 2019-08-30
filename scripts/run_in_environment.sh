#!/usr/bin/env bash
cat << EOF | singularity shell --bind /hadoop /cvmfs/singularity.opensciencegrid.org/efajardo/docker-cms\:tensorflow

source myenv/bin/activate
export PYTHONPATH=.:$PYTHONPATH
$@

EOF

