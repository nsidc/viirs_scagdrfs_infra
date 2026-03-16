#!/usr/bin/bash

source ${PWD}/config/env.sh
cd ${TOPDIR}

if { conda env list | grep 'viirs'; } >/dev/null 2>&1; then
    echo "setting conda to be a function for user $USER ..."
      __conda_setup="$('/home/$USER/miniconda3/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
      if [ $? -eq 0 ]; then
          eval "$__conda_setup"
      else
          if [ -f "/home/$USER/miniconda3/etc/profile.d/conda.sh" ]; then
              . "/home/$USER/miniconda3/etc/profile.d/conda.sh"
          else
              export PATH="/home/$USER/miniconda3/bin:$PATH"
          fi
      fi
      unset __conda_setup

    conda activate viirs

    echo "conda env should now be: viirs"
else
    echo "Creating conda environment."
    echo "Note; this might not work..."
    conda create -y -n viirs
    conda env update -f ${TOPDIR}/environment.yml
    conda init
    echo "And now activating viirs conda environment for the first time"
    conda activate viirs
fi

echo "Finished with activate-viirs-conda.sh at $(date)"
