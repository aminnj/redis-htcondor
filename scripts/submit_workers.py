#!/usr/bin/env python

import os
import tempfile
import argparse

template = """
universe                = vanilla
should_transfer_files   = YES
when_to_transfer_output = ON_EXIT_OR_EVICT
transfer_output_files = ""
Transfer_Executable     = True
transfer_input_files    = worker.py,workerenv.tar.xz
output                  = logs/1e.$(Cluster).$(Process).out
error                   = logs/1e.$(Cluster).$(Process).err
log                     = logs/$(Cluster).log
executable              = scripts/condor_executable.sh
RequestCpus = 1
RequestMemory = 8192
RequestDisk = 4096
+DESIRED_Sites="T2_US_UCSD"
+SingularityImage="/cvmfs/singularity.opensciencegrid.org/efajardo/docker-cms:tensorflow"
JobBatchName = "worker"
Requirements = ((HAS_SINGULARITY=?=True) && (HAS_CVMFS_cms_cern_ch =?= true) && {extra_requirements})
Arguments = {redis_url}
queue {num_workers}
"""

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("redis_url", help="redis url of the form redis://:password@hostname:port")
    parser.add_argument("-d", "--dry_run", help="echo submit file, but don't submit", action="store_true")
    parser.add_argument("-n", "--num_workers", help="number of workers", default=1, type=int)
    args = parser.parse_args()

    extra_requirements = "True"
    blacklisted_machines = [
            "sdsc-49.t2.ucsd.edu",
            "sdsc-50.t2.ucsd.edu",
            "cabinet-7-7-36.t2.ucsd.edu",
            "cabinet-8-8-1.t2.ucsd.edu",
            ]
    if blacklisted_machines:
        extra_requirements = " && ".join(map(lambda x: '(TARGET.Machine != "{0}")'.format(x),blacklisted_machines))

    content = template.format(
            extra_requirements=extra_requirements,
            num_workers=args.num_workers,
            redis_url=args.redis_url,
            )

    f = tempfile.NamedTemporaryFile(delete=False)
    filename = f.name
    f.write(content)
    f.close()

    if args.dry_run:
        print(content)
    else:
        os.system("mkdir -p logs/")
        os.system("condor_submit " + filename)

    f.unlink(filename)

