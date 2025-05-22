
## Setup block ##
import os 
import json
import pandas as pd
import numpy as np
from pathlib import Path
#for plotting cluster reports

from datetime import datetime
from IPython.display import Image, display 
import glob
import torch 
import logging
from spikeinterface import core as si
from spikeinterface import extractors as se
from spikeinterface import sorters as ss
from spikeinterface import curation as sc
from spikeinterface import preprocessing as sp

from probeinterface import get_probe



CODE_DIRECTORY = '/ceph/behrens/mingyu_zhu/vHPC_mPFC/code' #containing SpikeSorting folder
os.chdir(CODE_DIRECTORY)

mouseID = 'mz10'
target_date = '2024-10-24'
probe_type = get_probe('cambridgeneurotech','ASSY-156-P-1') ## change this to he probe type, for example: ASSY-156-P-1; ASSY-236-F
num_channels = 64  # Update with the actual number of channels



### things that probably don't need changing 
dtype = "int16"
probe_type.set_device_channel_indices(np.arange(num_channels))

EPHYS_PATH = Path("../data/raw_data/ephys") 
CONCAT_PATH = Path("../data/preprocessed_data/concat_ephys") 
SPIKESORTING_PATH = Path("../data/preprocessed_data/spikesorting_concat")
SAMPLING_FREQUENCY = 30000 

### this is to log the output of the behavioural preprocessing, the log file is saved in the same folder as the behavioural preprocessing script
# Define log file path
log_fp = os.path.join(os.getcwd(), 'mazeABCD_preprocessing_ephys','jobs', 'run_kilosort.log')
os.makedirs(os.path.dirname(log_fp), exist_ok=True)

# Create or get logger
logger = logging.getLogger('notebook_logger')
logger.setLevel(logging.DEBUG)  # Make sure all levels are allowed

# Remove any existing handlers (important in Jupyter!)
if logger.hasHandlers():
    logger.handlers.clear()

# Create file handler
file_handler = logging.FileHandler(log_fp, mode='a')
file_handler.setLevel(logging.DEBUG)  # Ensure handler accepts all levels

# Formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Add handler to logger
logger.addHandler(file_handler)

# Force flush (optional, helpful in notebooks)
file_handler.flush()
# Confirm file path

if torch.cuda.is_available() == False:
    logger.warning("No GPU available, using CPU")
else:
    logger.info("GPU available")



### essentialy functions 

def run_kilosort4(preprocessed_rec, preprocessed_path, kilosort_Ths=[9,8], IBL_preprocessing = True):
    """ Runs kilosort4 after preprocessing using spike-interface.
    We allow changes to Th_universal and Th_learned for optimisation, leaving all other parameters default.
    Note that we also toggle IBL_preprocessing here, as this will stop kilosort preprocessing/"""
    kilosort_output_path = preprocessed_path / f"kilosort4_preprocessing{IBL_preprocessing}"
    #load best Th parameters if kilosort parameters have been optimised. Otherwise default is given above.
    if (SPIKESORTING_PATH/'kilosort_optim'/'best_params.json').exists(): 
        with open(SPIKESORTING_PATH/'kilosort_optim'/'best_params.json', 'r') as f:
            kilosort_Ths = json.load(f)
    if not (preprocessed_path/f"kilosort4_preprocessing{IBL_preprocessing}").exists(): #if the ks folder exists, assume sorting completed with no bugs.
        print("running Kilosort4")
        kilosort_output_path.mkdir(parents=True)
        
        #Set up parameters for kilosort
        sorter_params = ss.get_default_sorter_params("kilosort4")
        #For optional changes to kilosort parameters
        sorter_params["Th_universal"] = kilosort_Ths[0]
        sorter_params["Th_learned"] = kilosort_Ths[1]
        if IBL_preprocessing == True:
            sorter_params["do_CAR"] = False #we perform IBL destriping instead using spikeinterface
        n_shanks = len(np.unique(preprocessed_rec.get_property('group')))
        if n_shanks == 1:
            sorter_params["nblocks"] = 1 #Default is 1 (rigid), 5 is recommended for single shank neuropixel. Shouldn't have a big influence regardless.
        
        sorter = ss.run_sorter(
            "kilosort4",
            recording=preprocessed_rec,
            folder=kilosort_output_path,
            verbose=True,
            remove_existing_folder=True,
            **sorter_params,
        )
        sorter = sc.remove_excess_spikes(sorter, preprocessed_rec)
        sorter = sorter.remove_empty_units()
    else:  # if ks already run load sorter
        print("loading Kilosort4 output")
        sorter = ss.read_sorter_folder(
            kilosort_output_path,
            register_recording=preprocessed_rec,
        )
    return sorter




logger.info(f"Dealing with {mouseID} on {target_date} with Kilosort4")

if os.path.isdir(SPIKESORTING_PATH) == False:
    os.mkdir(SPIKESORTING_PATH)


if os.path.isdir(SPIKESORTING_PATH/mouseID) == False:
    os.mkdir(SPIKESORTING_PATH/mouseID)

OUTPUT_PATH = SPIKESORTING_PATH/mouseID/target_date
if os.path.isdir(OUTPUT_PATH) == False:
    os.mkdir(OUTPUT_PATH)


concat_ephys_fp_for_kilosort = glob.glob(f"{CONCAT_PATH}/{mouseID}/*{target_date}*/**/*binary.dat", recursive=True)
recording = se.BinaryRecordingExtractor(concat_ephys_fp_for_kilosort, 
                                        dtype='int16', 
                                        num_channels=64, 
                                        sampling_frequency=SAMPLING_FREQUENCY)

print(recording)
logger.info(f"session length detected as {recording.get_num_frames()/SAMPLING_FREQUENCY/60} minutes")

recording_shanks = recording.set_probe(probe_type, group_mode='by_shank')

sorting = run_kilosort4(recording_shanks, OUTPUT_PATH, IBL_preprocessing=False)





