# Preprocessing Maze Ephys Data with SpikeInterface & Kilosort4

# this is a relatively simple workflow that deals with concatenation, kilosort, manual spikesorting,

## STEP 1: Create a new environment
- create new conda environment 
    ``` bash 
    conda create --name maze_ephys python==3.12.7
    conda activate maze_ephys
    ```
- install required packages (assuming you're in .../experiment/code)
    ``` bash 
    pip install -r SpikeSorting/requirements.txt
    ```

## STEP 2: Organise Your Ephys Data

 - We're expecting data which is structured as follows:
    ```python
    .
    └── experiment/ 
        ├── code/ 
        │   └── ... <-- (you are somewhere here)
        └── data/ 
            ├── ... 
            ├── raw_data/
            │   ├── ...
            │   └── ephys/
            │       └── [subject_ID]/
            │           └── [datetime]/
            │               └── [Open Ephys data]...
            │   └── metadata/
            │       └── MetaData-{subject_id}
            │       └── ...
            └── preprocessed_data/
                ├── ...
                └── concat_ephys ### concatenated ephys data 
                    └── [subject_ID]/
                        └── [datetime]/
                            └── [datetime_timestamp_for_concat_time]
                └── spikesorting_concat ### kilosort output of concatenated ephys data 
                    └── [subject_ID]/
                        └── [datetime] ## if concatenating by single day 
                └── spikesorting_concat_done ## if doing manual spikesorting 
                    └── [subject_ID]/
                        └── [datetime] ## if concatenating by single day 
    ```

 - Make sure your current directory is the 'code' folder
    ``` bash
        cd <.../experiment/code>
    ```
    
## STEP 3: Concatenating (if needed)

 - very straightforward with spikeinterface. click open the concatenating_spikeinterface.py file, change the subject_id and the target_date, check that the sessions selected are indeed the ones that you would want to include (the code will read through the metadata to find the sessions that are included for analyses, so make sure that the metadata file has been checked )
 - this whould generate within your /concat_ephys/<subject_id>/<target_date> folder,

        ├── binary.dat  ## the actual concatenated data 
        ├── binary.json ## needed by spikeinterface to do kilosort 
        └── concat_info.csv ## this keeps tracks which sessions are being concatenated here, and the size of the session to that we can use it later to split the concatenated data back into individual sessions. 
 - to do that, simply 
     ``` bash
        cd <.../code/mazeABCD_preprocessing_ephys>
        module load miniconda
        conda activate maze_ephys
        python concatenating_spikeinterface.py 
    ```

 ## STEP 4: submit the job to the cluster for kilosorting 

 - the current script uses kilosort4, but without any IBL_prepreocessing, if you wish to do IBL preprocessing, it's worth going Peter and Charles' repo SpikeSorting (THIS IS STRONGLY RECOMMENDED ESPECIALLY IF YOU'RE USING NEUROPIXEL)
 - what you need to do: 

 - open the run_kilosort.py file, and change the subject_id and target_date (similar to concatenating)
 - then in terminal, simply run 

      ``` bash
         chmod +x submit_run_KS.sh ### make sure that the files are executable 
         chmod +x run_KS.sbatch 
         ./submit_run_KS.sh ## submit the job to cluster 
    ```
    this would submit the job to cluster, you can check the output/error and the log of running the .py file under the /jobs folder 

 - at the end you should have: 

    ```python
    .
    └── experiment/ 

        └── data/ 
            └── preprocessed_data/
                └── spikesorting_concat ### kilosort output of concatenated ephys data 
                    └── [subject_ID]/
                        └── [datetime]/ ## if concatenating by single day 
                            └── kilosort4_preprocessingFalse/
                                └── sorter_output/
    ```

## STEP 5: manual curation 

 - download the output of the kilosort4 (download the whole /sorter_output folder), to your local PC -- ideally not Mac, current M- chips are NOT supporting phy (which we need to use for manual curation), if you have one of the old Macbook that uses Intel, you could get around by doing what some users are suggesting on the github forums, check specifics here: https://github.com/cortex-lab/phy/issues/1260

 - if you have any non-Mac PC, nice! Install phy and enjoy spikesorting!  (or try to).  you'd probably need to talk to someone if you're new to this.

 - after spikesorting has been done, upload the following three files onto the /spikesorting_concat_done/<subject_id>/<datetime> folder

    ```python
      └── experiment/ 

        └── data/ 
            └── preprocessed_data/
                └── spikesorting_concat_done ### kilosort output of concatenated ephys data 
                    └── [subject_ID]/
                        └── [datetime]/ ## if concatenating by single day 
                            ├── cluster_group.tsv  
                            ├── spike_clusters.npy 
                            └── spike_times.npy  
    ```


 - you might wonder, what are these files? Each cluster has a unique cluster id, `cluster_group.tsv` tells you whether a cluster is a good cluster or a MUA, `spike_clusters.npy` and `spike_times.tsv` tell you the info regarding the spike that has occured in a sequential manner. For each spike, `spike_clusters.npy` tells you the cluster_id that the spike belongs to, and `spike_times.tsv` tells you what time it has occurred (the sampling rate here should be 30000Hz). 

 ## STEP 6: splitting the curated data into sessions and generate the neuron_raw.npy files 

  - Hooray! The hardest, most eye-tiring part has been done! We do need to format the data in a easier way for us to analyse. usually we name the files as  `Neuron_raw_{subject_id}_{datetime}_{session_number}.npy`, and it should be saved under: 

    ```python
      └── experiment/ 

        └── data/ 
            └── preprocessed_data/
                ├── Neuron_raw_mz06_20241022_0.npy # for example 
                ├── Neuron_raw_mz06_20241022_1.npy
                ├── Neuron_raw_mz06_20241023_0.npy
                ├── Neuron_raw_mz06_20241023_1.npy
                ├── ... 
    ```

 - the Neuron_raw_.npy are arrays of shape ((number_of_neurons, time_bins)) in 40 Hz (i.e. 25ms timebins), it's aligned to pycontrol data, and trimmed according to the first A and last A the animal has received -- similar to behavioural data. 

 - to do that, you need the preprocess_ephys_functions.py and spikesorted_to_neuron_raw.py file. click open <spikesorted_to_neuron_raw.py> and change the mouse_id and target_date. If you have made some mistakes during ephys acquisition (e.g. starting pycontrol before starting OpenEphys) set EPHYS_VIDEO_MISMATCH == True -- this tells the code that the syncpulses might not match perfectly -- you should consider discarding this or adjust this manually. 
 
 and then, in the terminal within your /code directory, similar to 

      

      ``` bash
        module load miniconda 
        conda activate maze_ephys 
        python -m mazeABCD_preprocessing_ephys.spikesorted_to_neuron_raw 
    ```





