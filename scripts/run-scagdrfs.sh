#!/bin/bash

# Record the start time
start_time=$(date +%s)

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

# Load environment and activate conda
set +u
source ${PROJECT_ROOT}/scripts/activate-viirs-conda.sh
set +u

python -m src.run_scagdrfs "$@"

# Record the end time
end_time=$(date +%s)

# Calculate and report the elapsed time
elapsed=$(( end_time - start_time ))
echo "Elapsed time: $elapsed seconds"
