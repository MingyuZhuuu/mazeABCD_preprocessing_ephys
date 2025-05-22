#!/bin/bash

# Generate current timestamp
timestamp=$(date +"%Y-%m-%d_%H-%M-%S")

# Define job name
jobname="run_KS_mingyu" ### you could change the name 

# Define output and error log file paths with timestamp
out_path="/ceph/behrens/mingyu_zhu/vHPC_mPFC/code/mazeABCD_preprocessing_ephys/jobs/out/${jobname}_${timestamp}.out"
err_path="/ceph/behrens/mingyu_zhu/vHPC_mPFC/code/mazeABCD_preprocessing_ephys/jobs/err/${jobname}_${timestamp}.err"

# Submit the job with the dynamically generated log paths
sbatch --job-name="$jobname" \
       --output="$out_path" \
       --error="$err_path" \
       run_KS.sbatch