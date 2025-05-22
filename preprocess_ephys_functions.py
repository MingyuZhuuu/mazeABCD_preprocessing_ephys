import os 
import json
import pandas as pd
import numpy as np
from pathlib import Path


import glob
import warnings

def load_metadata(mouse_id, raw_data_path):
    metadata_fp = raw_data_path / 'metadata' / f'MetaData_{mouse_id}.csv'
    return pd.read_csv(metadata_fp)


def load_concat_info(concat_path, mouse_id, target_date):
    # Find the most recent concat folder for the mouse/date
    concat_dir = concat_path / mouse_id / target_date
    all_concat_folders = sorted(concat_dir.glob('*'), key=os.path.getmtime, reverse=True)
    if not all_concat_folders:
        raise FileNotFoundError(f'No concat folders found for {mouse_id} on {target_date}')
    target_concat_folder = all_concat_folders[0]
    concat_info_fp = target_concat_folder / 'concat_info.csv'
    concat_info_df = pd.read_csv(concat_info_fp)
    return concat_info_df, target_concat_folder

def build_output_file_lists(metadata_currday, concat_info_df, neuron_raw_path, mouse_id, target_date):
    included_sessions = metadata_currday[metadata_currday['Include'] == 1]
    sess_num_handle = []
    sess_num_handle_list = []
    for concat_sess in concat_info_df['date_session']:
        sess_num_handle_list.append(concat_sess.split('_')[-1])

    for sess in range(len(included_sessions)):
        if included_sessions.iloc[sess]['Ephys'] in sess_num_handle_list:
            sess_num_handle.append(sess)
            
    neuron_raw_fp_list = []
    subject_date_str = f'{mouse_id}_{target_date.replace("-", "")}'
    for i, row in concat_info_df.iterrows():
        neuron_raw_fp_list.append(neuron_raw_path / f'Neuron_raw_{subject_date_str}_{sess_num_handle[i]}.npy')
    return neuron_raw_fp_list


def find_ephys_sync_file(ephys_path, mouse_id, date_session):
    # Recursively search for TTL/timestamps.npy in the session folder
    search_path = Path(ephys_path) / mouse_id / date_session
    matches = list(search_path.glob("**/experiment1/recording1/events/**/TTL/sample_numbers.npy"))
    if not matches:
        raise FileNotFoundError(f"No ephys sync file found for {date_session}")
    return matches[0]

def find_ephys_sync_state_file(ephys_path, mouse_id, date_session):
    search_path = Path(ephys_path) / mouse_id / date_session
    matches = list(search_path.glob("**/experiment1/recording1/events/**/TTL/states.npy"))
    if not matches:
        raise FileNotFoundError(f"No ephys sync file found for {date_session}")
    return matches[0]

def find_pycontrol_file(behaviour_path, mouse_id, target_date, pycontrol_id):
    # Handles leading zeros for pycontrol_id
    if int(pycontrol_id) < 100000:
        fname = f"{mouse_id}-{target_date}-0{int(pycontrol_id)}.txt"
    else:
        fname = f"{mouse_id}-{target_date}-{int(pycontrol_id)}.txt"
    fpath = Path(behaviour_path) / fname
    if not fpath.exists():
        raise FileNotFoundError(f"No pyControl file found: {fpath}")
    return fpath

def count_ephys_sync_pulses(sync_state_fp):
    arr = np.load(sync_state_fp)
    possible_states = np.unique(abs(arr))
    # Count occurrences of each
    counts =    np.array([np.sum(arr == state) for state in possible_states])
    return possible_states, counts

def count_pycontrol_rsync_pulses(pycontrol_fp):
    count = 0
    with open(pycontrol_fp, 'r') as f:
        for line in f:
            if 'rsync' in line: 
                event_dict = json.loads(line[2:])
                ind = event_dict['rsync']
                #print(ind)
            if line.startswith('D '):  # Data lines
                parts = line[2:].strip().split()
                timestamp = float(parts[0])
                event_code = int(parts[1])
                if event_code == ind:
                    count +=1 
    return count

def build_and_check_file_lists(concat_info_df, metadata_currday, ephys_path, behaviour_path, mouse_id, target_date, ephys_video_mismatch = False):
    pycontrol_fp_list = []
    ephys_sync_samplenumber_fp_list = []
    ephys_sync_state_fp_list = []
    ephys_video_mismatch_list = []
    
    for i, row in concat_info_df.iterrows():
        date_session = row['date_session']
        # Find ephys sync fil
        ephys_sync_fp = find_ephys_sync_file(ephys_path, mouse_id, date_session)
        ephys_sync_samplenumber_fp_list.append(ephys_sync_fp)
        ephys_sync_state_fp = find_ephys_sync_state_file(ephys_path, mouse_id, date_session)
        ephys_sync_state_fp_list.append(ephys_sync_state_fp)
        # Find pyControl file
        # Map ephys session to pyControl session using metadata
        ephys_sess_id = date_session.split('_')[-1]
        # Find the row in metadata_currday where Ephys matches ephys_sess_id
        meta_row = metadata_currday[metadata_currday['Ephys'] == ephys_sess_id]
        if meta_row.empty:
            warnings.warn(f"No metadata match for ephys session {ephys_sess_id}")
            pycontrol_fp_list.append(None)
            continue
        pycontrol_id = meta_row['Behaviour'].iloc[0]
        pycontrol_fp = find_pycontrol_file(behaviour_path, mouse_id, target_date, pycontrol_id)
        pycontrol_fp_list.append(pycontrol_fp)
        # Check sync pulses
        state_ephys, n_ephys = count_ephys_sync_pulses(ephys_sync_state_fp)
        n_pycontrol = count_pycontrol_rsync_pulses(pycontrol_fp)

        if n_pycontrol not in n_ephys:
            warnings.warn(f"Sync pulse mismatch for session {date_session}: Ephys={n_ephys}, PyControl={n_pycontrol}")
            if n_pycontrol > min(n_ephys) and ephys_video_mismatch:
                ephys_video_mismatch_list.append(True)
                print(f"video ended before ephys ended for session {date_session},Ephys={n_ephys}, PyControl={n_pycontrol}")
            elif ephys_video_mismatch:
                ephys_video_mismatch_list.append(False)
        else:
            
            stateidx = np.where(n_ephys == n_pycontrol)[0][0]
            state_ephys_curr = state_ephys[stateidx]
            print(f"Session {date_session}: Sync pulses match, no. of sync pulses: {n_pycontrol}")
            if ephys_video_mismatch:
                ephys_video_mismatch_list.append(False)
    return pycontrol_fp_list, ephys_sync_samplenumber_fp_list, ephys_sync_state_fp_list, ephys_video_mismatch_list

def find_first_ephys_sync_pulse(pycontrol_fp, ephys_sync_states_fp, ephys_sync_samplenumber_fp, ephys_video_mismatch_list_curr = False):
    state_ephys, n_ephys = count_ephys_sync_pulses(ephys_sync_states_fp)
    n_pycontrol = count_pycontrol_rsync_pulses(pycontrol_fp)
    if ephys_video_mismatch_list_curr:
        stateidx = np.where(n_ephys < n_pycontrol)[0]
        #print(n_ephys, n_pycontrol, stateidx)
    else:
        stateidx = np.where(n_ephys == n_pycontrol)[0][0]
    state_ephys_curr = state_ephys[stateidx]
    state_array = np.load(ephys_sync_states_fp)
    samplenumber_array = np.load(ephys_sync_samplenumber_fp)
    timestamp_ind = np.where(state_array == state_ephys_curr)[0][0]
    curr_timestamp = samplenumber_array[timestamp_ind]
    return curr_timestamp

def find_firstA_lastA(pycontrol_fp, sampling_frequency = 1000/40):
    timestamp_array=[]
    with open(pycontrol_fp, 'r') as f:
        for line in f:
            if 'A_on' in line: 
                event_dict = json.loads(line[2:])
                ind = event_dict['A_on']
                #print(ind)
            if line.startswith('D '):  # Data lines
                parts = line[2:].strip().split()
                timestamp = float(parts[0])
                event_code = int(parts[1])
                
                if event_code == ind:
                    timestamp_array.append(int(timestamp/sampling_frequency))
    return timestamp_array[0], timestamp_array[-1]

def extract_spike_data(spikesorting_path, mouseID, target_date, concat_info_df, first_timestamp_list, first_A_frame_list, last_A_frame_list, neuron_raw_fp_list, rebin_factor = 30000/40):
    cluster_group = pd.read_csv(spikesorting_path/mouseID/target_date/'cluster_group.tsv',sep='\t')
    spike_clusters = np.load(spikesorting_path/mouseID/target_date/'spike_clusters.npy')
    spike_times = np.load(spikesorting_path/mouseID/target_date/'spike_times.npy')

    good_clu = np.array(cluster_group[cluster_group['group'] == 'good']['cluster_id'])

    firing_array = np.zeros(shape = (len(good_clu), np.sum(concat_info_df['num_sample'])))
    for i,clu in enumerate(good_clu):
        find_ind = np.where(spike_clusters==clu)[0]
        spike_time_clu = [spike_times[ind] for ind in find_ind]
        firing_array[i,spike_time_clu] = 1  

    for sess in range(len(concat_info_df)):
        if sess == 0:
            start = 0 
            end = concat_info_df['num_sample'][sess]
        else:
            end = start + concat_info_df['num_sample'][sess]
        curr_sess = firing_array[:,start:end]
        #print(curr_sess.shape)
        curr_sess = curr_sess[:,first_timestamp_list[sess]:]
        #print(curr_sess.shape)
        start += concat_info_df['num_sample'][sess]
        new_cols = curr_sess.shape[1] // rebin_factor
        #print(new_cols)
        #curr_sess_reshaped = curr_sess.reshape((len(curr_sess),int(new_cols),int(rebin_factor)))
        #print(curr_sess_reshaped.shape)
        trimmed_data = curr_sess[:, :int(new_cols) * int(rebin_factor)]

        # Reshape and average
        rebinned_data =  trimmed_data.reshape(curr_sess.shape[0], int(new_cols), int(rebin_factor)).sum(axis=2)
        #print(rebinned_data.shape)  

        rebinned_data_aligned = rebinned_data[:,first_A_frame_list[sess]:last_A_frame_list[sess]]
        #print(rebinned_data_aligned.shape)


        np.save(neuron_raw_fp_list[sess], rebinned_data_aligned)
        print(f"neuron firing data of shape {rebinned_data_aligned.shape} saved to {neuron_raw_fp_list[sess]}")
        




