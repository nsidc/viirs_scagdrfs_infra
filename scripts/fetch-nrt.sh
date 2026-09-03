#!/bin/bash
# Fetch VIIRS VJ109GA Near Real-Time (NRT) data
set -euo pipefail


# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

# Load environment and activate conda
set +u
source ${PROJECT_ROOT}/scripts/activate-viirs-conda.sh
set +u

# Run the fetch module
python3 -m src.fetch_nrt "$@"
