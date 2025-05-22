import os 
import json
import pandas as pd
import numpy as np
from pathlib import Path
#for plotting cluster reports
from datetime import datetime
import glob

CODE_DIRECTORY = '/ceph/behrens/mingyu_zhu/vHPC_mPFC/code' #containing SpikeSorting folder
os.chdir(CODE_DIRECTORY)

from spikeinterface import core as si
from spikeinterface import extractors as se

EPHYS_PATH = Path("../data/raw_data/ephys") 
CONCAT_PATH = Path("../data/preprocessed_data/concat_ephys") 
SPIKESORTING_PATH = Path("../data/preprocessed_data/spikesorting_concat")
METADATA_PATH = Path("../data/raw_data/metadata")

SAMPLING_FREQUENCY = 30000 
dtype = "int16"

#### things to change 
mouseID = 'mz10'
num_channels = 64 

target_date = '2024-10-24'

metadata= pd.read_csv(METADATA_PATH/f"MetaData_{mouseID}.csv")
include= list(metadata.loc[(metadata['Date'] == target_date)]['Include'])

## put in the sessions to include manually 


curr_timestamp =datetime.now().isoformat()


if os.path.isdir(CONCAT_PATH) == False:
    os.mkdir(CONCAT_PATH)

if os.path.isdir(CONCAT_PATH/mouseID) == False:
    os.mkdir(CONCAT_PATH/mouseID)

OUTPUT_PATH = CONCAT_PATH/mouseID/target_date
if os.path.isdir(OUTPUT_PATH) == False:
    os.mkdir(OUTPUT_PATH)


target_ephys_fp = glob.glob(f"{EPHYS_PATH}/{mouseID}/*{target_date}*", recursive=True)  
target_ephys_fp_list = glob.glob(f"{EPHYS_PATH}/{mouseID}/*{target_date}*/**/experiment1/recording1/**/continuous.dat", recursive=True)  
target_ephys_fp_list = sorted(target_ephys_fp_list)
if len(target_ephys_fp)!= len(include):
    print("Error, number of sessions to consider does not match file found")
date_time_str_list = []
for i in range(len(target_ephys_fp)):
    date_time_str_list.append(target_ephys_fp[i].split('/')[-1])
date_time_str_list = sorted(date_time_str_list)

print(f"{len(target_ephys_fp)} files found for {mouseID}, on {target_date}, with {len(date_time_str_list)} sessions: ", date_time_str_list)

print("including session:")

target_ephys_fp_list_trimmed=[]
date_time_str_list_trimmed = []
for i in range(len(include)):
    if include[i] != 1:
        continue
    else:
        target_ephys_fp_list_trimmed.append(target_ephys_fp_list[i])
        date_time_str_list_trimmed.append(date_time_str_list[i])
        print(date_time_str_list[i])


cont = input('do you want to proceed with merge?')



if str(cont) == 'yes':

    output_filename = OUTPUT_PATH/f"{target_date}_{curr_timestamp}"
    if os.path.isdir(output_filename) == False:
        os.mkdir(output_filename)

    binary_output_fp = output_filename/'binary.dat'

    num_sample_list = []
    if len(target_ephys_fp_list_trimmed) == 1:
        concat_rec = se.read_binary(target_ephys_fp_list_trimmed[0], num_channels=num_channels, sampling_frequency=SAMPLING_FREQUENCY, dtype=dtype)
        num_sample_list.append(concat_rec.get_num_samples())
    else:    
        for i in range(len(target_ephys_fp_list_trimmed)):
            if i == 0:
                recording1 = se.read_binary(target_ephys_fp_list_trimmed[i], num_channels=num_channels, sampling_frequency=SAMPLING_FREQUENCY, dtype=dtype)
                recording2 = se.read_binary(target_ephys_fp_list_trimmed[i+1], num_channels=num_channels, sampling_frequency=SAMPLING_FREQUENCY, dtype=dtype)
                concat_rec = si.concatenate_recordings([recording1, recording2])
                num_sample_list.append(recording1.get_num_samples())
                num_sample_list.append(recording2.get_num_samples())

            elif i == 1:
                continue
            else:
                recording_curr = se.read_binary(target_ephys_fp_list_trimmed[i], num_channels=num_channels, sampling_frequency=SAMPLING_FREQUENCY, dtype=dtype)
                num_sample_list.append(recording_curr.get_num_samples())
                concat_rec = si.concatenate_recordings([concat_rec, recording_curr])

    si.write_binary_recording(concat_rec, file_paths=binary_output_fp)

    metadata = {
        "sampling_frequency": 30000,  # Adjust if different
        "num_channels": concat_rec.get_num_channels(),
        "dtype": "int16",
        "gain": 1.0,  # Adjust if needed
        "offset": 0
    }

    # Save as binary.json
    with open(f"{output_filename}/binary.json", "w") as f:
        json.dump(metadata, f, indent=4)

    print("binary.json saved!")

    concat_info_df = pd.DataFrame({
        'subject_ID':np.repeat(mouseID,len(date_time_str_list_trimmed)),
        'date_session':date_time_str_list_trimmed,
        'ephys_path':target_ephys_fp_list_trimmed,
        'num_sample':num_sample_list,
    })
    print(concat_info_df)

    concat_info_df.to_csv(f"{output_filename}/concat_info.csv", index = False)

    print("concat_info.csv saved!")

