#!/usr/bin/bash

CONDA_BASE="${CONDA_BASE:-/home/$USER/miniconda3}"
source "${CONDA_BASE}/etc/profile.d/conda.sh"

if conda env list | awk '{print $1}' | grep -qx viirs; then
    echo "Activating viirs conda environment."
    conda activate viirs
else
    echo "Creating viirs conda environment."
    conda env create -y -n viirs -f environment.yml
    echo "Activating viirs conda environment."
    conda activate viirs
fi
echo "Finished with activate-viirs-conda.sh at $(date)"
