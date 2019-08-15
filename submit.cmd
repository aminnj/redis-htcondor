universe                = vanilla
should_transfer_files   = YES
when_to_transfer_output = ON_EXIT_OR_EVICT
transfer_output_files = ""
Transfer_Executable     = True
transfer_input_files    = worker.py,workerenv.tar.xz
output                  = logs/1e.$(Cluster).$(Process).out
error                   = logs/1e.$(Cluster).$(Process).err
log                     = logs/$(Cluster).log
executable              = executable.sh
+DESIRED_Sites="T2_US_UCSD"
+taskname = "mytask1"
+SingularityImage="/cvmfs/singularity.opensciencegrid.org/efajardo/docker-cms:tensorflow"
JobBatchName = "worker"
Requirements = ((HAS_SINGULARITY=?=True) && (HAS_CVMFS_cms_cern_ch =?= true))
