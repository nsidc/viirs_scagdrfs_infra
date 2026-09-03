#!/usr/bin/bash

source ${PWD}/config/env.sh
cd ${TOPDIR}

if { conda env list | grep 'viirs'; } >/dev/null 2>&1; then
    echo "Activating viirs conda environment."
    source activate viirs
else
    echo "Creating viirs conda environment."
    conda create -y -n viirs
    conda env update -f ${TOPDIR}/environment.yml
    echo "Activating scag conda environment."
    conda activate viirs
fi
echo "Finished with activate-viirs-conda.sh at $(date)"
