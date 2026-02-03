#!/bin/bash
# Fetch VIIRS VJ109GA Near Real-Time (NRT) data
set -euo pipefail


# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

# Load environment and activate conda
source "${PROJECT_ROOT}/config/env.sh"

# Run the fetch module
python3 -m src.fetch_nrt "$@"
