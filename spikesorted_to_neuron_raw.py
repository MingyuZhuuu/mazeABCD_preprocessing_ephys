import os 
import json
import pandas as pd
import numpy as np
from pathlib import Path

import sys

sys.path.append(str(Path(__file__).parent))
import glob
import warnings
from mazeABCD_preprocessing_ephys.preprocess_ephys_functions import *

### IMPORTANT PARAMETERS: change each time 
MOUSE_ID = 'mz06'
TARGET_DATE = '2024-10-26'
EPHYS_VIDEO_MISMATCH = False ## keep False, unless you want to deal with video ended before ephys ended

CODE_DIRECTORY = '/ceph/behrens/mingyu_zhu/vHPC_mPFC/code' #containing SpikeSorting folder
os.chdir(CODE_DIRECTORY)


### parameters that should stay the same 
PREPROCESSING_PARAMS_FOLDER = Path("preprocessing/params")
RAW_DATA_PATH =  Path("../data/raw_data") 
EPHYS_PATH = RAW_DATA_PATH/'ephys'
BEHAVIOUR_PATH = RAW_DATA_PATH/'behaviour'
CONCAT_PATH = Path("../data/preprocessed_data/concat_ephys") 
SPIKESORTING_PATH = Path("../data/preprocessed_data/spikesorting_concat")
SPIKESORTING_DONE_PATH = Path("../data/preprocessed_data/spikesorting_concat_done")
NEURON_RAW_PATH=Path("../data/preprocessed_data/neuron_raw")
SAMPLING_FREQUENCY = 30000 
dtype = "int16"

### processing starts here 
print(f"Dealing with {MOUSE_ID} on {TARGET_DATE}")

if os.path.isdir(NEURON_RAW_PATH) == False:
    os.mkdir(NEURON_RAW_PATH)

if os.path.isdir(SPIKESORTING_DONE_PATH) == False:
    print("spikeing sorted data not found")
    exit()

path_pattern = os.path.join(CONCAT_PATH, MOUSE_ID, TARGET_DATE, '**', 'concat_info.csv')
matches = glob.glob(path_pattern, recursive=True)

if not matches:
    print("concat_info.csv not found.")

concat_info_df, target_concat_folder = load_concat_info(CONCAT_PATH, MOUSE_ID, TARGET_DATE)
print(f"sessions concatenated:\n{concat_info_df['date_session']}")

cont = input('do you want to proceed with splitting data into Neuron_raw.npy?')



if str(cont) == 'yes':

###### 

### step1: loading the metadata, concat_info_df, target_concat_folder
    metadata = load_metadata(MOUSE_ID, RAW_DATA_PATH)
    metadata_currday = metadata[metadata['Date'] == TARGET_DATE]
    #concat_info_df, target_concat_folder = load_concat_info(CONCAT_PATH, MOUSE_ID, TARGET_DATE)


    ### step2: building the file lists to read from and save to 
    neuron_raw_fp_list = build_output_file_lists(metadata_currday, concat_info_df, NEURON_RAW_PATH, MOUSE_ID, TARGET_DATE)
    #print(neuron_raw_fp_list)

    pycontrol_fp_list, ephys_sync_samplenumber_fp_list,ephys_sync_state_fp_list, ephys_video_mismatch_list = build_and_check_file_lists(
        concat_info_df, metadata_currday, EPHYS_PATH, BEHAVIOUR_PATH, MOUSE_ID, TARGET_DATE, EPHYS_VIDEO_MISMATCH
    )

    ### step3: finding the timestamps, firstA frame, lastA frame, for alignment. load the spikesorting results, split, align, save. 
    first_rsync_samplenumber = []
    first_A_frame_list = []
    last_A_frame_list = []

    for i in range(len(concat_info_df)):
        if EPHYS_VIDEO_MISMATCH:
            timestamp_curr = find_first_ephys_sync_pulse(pycontrol_fp_list[i], ephys_sync_state_fp_list[i], ephys_sync_samplenumber_fp_list[i], ephys_video_mismatch_list[i])
        else:
            timestamp_curr = find_first_ephys_sync_pulse(pycontrol_fp_list[i], ephys_sync_state_fp_list[i], ephys_sync_samplenumber_fp_list[i])
        firstA, lastA = find_firstA_lastA(pycontrol_fp_list[i])
        print(pycontrol_fp_list[i], timestamp_curr, firstA, lastA)
        first_rsync_samplenumber.append(timestamp_curr)
        first_A_frame_list.append(firstA)
        last_A_frame_list.append(lastA)

    extract_spike_data(SPIKESORTING_DONE_PATH, MOUSE_ID, TARGET_DATE, concat_info_df, first_rsync_samplenumber, first_A_frame_list, last_A_frame_list, neuron_raw_fp_list)



