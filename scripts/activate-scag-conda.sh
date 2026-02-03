#!/usr/bin/bash

source ${PWD}/config/env.sh
cd ${TOPDIR}

if { conda env list | grep 'scag'; } >/dev/null 2>&1; then
    echo "Activating scag conda environment."
    source activate scag
else
    echo "Creating scag conda environment."
    conda create -y -n scag
    conda env update -f ${TOPDIR}/environment.yml
    echo "Activating scag conda environment."
    conda activate scag
fi
