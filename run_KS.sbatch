#!/bin/bash

#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=10
#SBATCH -p gpu
#SBATCH --gres=gpu:1
#SBATCH --mem=64G
#SBATCH --time=48:00:00

source /etc/profile.d/modules.sh

module load cuda
module load miniconda

conda deactivate
conda deactivate
conda deactivate
conda activate maze_ephys


# Run your Python script
python run_kilosort.py
