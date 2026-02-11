#!/usr/bin/bash

source ${PWD}/config/env.sh
cd ${TOPDIR}

if { conda env list | grep 'scag'; } >/dev/null 2>&1; then
    echo "Activating scag conda environment."
    source activate viirs 
else
    echo "Creating conda environment."
    conda create -y -n viirs 
    conda env update -f ${TOPDIR}/environment.yml
    echo "Activating viirs conda environment."
    conda activate viirs
fi
