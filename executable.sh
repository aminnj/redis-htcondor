#!/usr/bin/env bash

function getjobad {
    grep -i "^$1" "$_CONDOR_JOB_AD" | cut -d= -f2- | xargs echo
}

if [ -r "$OSGVO_CMSSW_Path"/cmsset_default.sh ]; then
    echo "sourcing environment: source $OSGVO_CMSSW_Path/cmsset_default.sh"
    source "$OSGVO_CMSSW_Path"/cmsset_default.sh
elif [ -r "$OSG_APP"/cmssoft/cms/cmsset_default.sh ]; then
    echo "sourcing environment: source $OSG_APP/cmssoft/cms/cmsset_default.sh"
    source "$OSG_APP"/cmssoft/cms/cmsset_default.sh
elif [ -r /cvmfs/cms.cern.ch/cmsset_default.sh ]; then
    echo "sourcing environment: source /cvmfs/cms.cern.ch/cmsset_default.sh"
    source /cvmfs/cms.cern.ch/cmsset_default.sh
else
    echo "ERROR! Couldn't find $OSGVO_CMSSW_Path/cmsset_default.sh or /cvmfs/cms.cern.ch/cmsset_default.sh or $OSG_APP/cmssoft/cms/cmsset_default.sh"
    exit 1
fi

ls -lrth

if ! ls /hadoop/cms/store/user/namin ; then
    echo "hadoop is not visible (?), so the worker would be useless later. dying."
    exit 1
else
    echo "found user dir in hadoop"
fi

# # cmsenv not needed with this singularity container
# export SCRAM_ARCH="slc7_amd64_gcc700"
# CMSSWVERSION="CMSSW_10_5_0"
# cmsrel $CMSSWVERSION
# cd $CMSSWVERSION
# cmsenv
# if [[ $? != 0 ]]; then
#     echo "cmsenv error, so maybe cvmfs is messed up"
#     exit 1
# fi

mkdir temp
cd temp
mv ../workerenv.tar.xz .
mv ../worker.py .

tar xf workerenv.tar.xz
ls -lrth
export PATH=`pwd`/workerenv/bin:$PATH

echo $PATH
echo $PYTHONPATH

which python3
which pip3
python3 -V
python3 worker.py $@

