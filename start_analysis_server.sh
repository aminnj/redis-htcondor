#!/usr/bin/env bash

singularity exec --bind /hadoop /cvmfs/singularity.opensciencegrid.org/efajardo/docker-cms\:tensorflow  ./setup_analysis_container.sh
