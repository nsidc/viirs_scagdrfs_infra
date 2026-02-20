#!/bin/bash

# Record the start time
start_time=$(date +%s)

source ${PWD}/config/env.sh
source ${PWD}/scripts/activate-viirs-conda.sh
python -m src.run_scagdrfs "$@"

# Record the end time
end_time=$(date +%s)

# Calculate and report the elapsed time
elapsed=$(( end_time - start_time ))
echo "Elapsed time: $elapsed seconds"
