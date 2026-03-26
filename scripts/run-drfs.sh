#!/bin/bash

echo
echo "'source'ing env.sh..."
source ${PWD}/config/env.sh

echo
echo "activating conda env 'scag'..."
echo "SKIPPING..."
#source ${PWD}/scripts/activate-scag-conda.sh

echo
echo "Invoking run_drfs..."
echo "   python -m scagdrfs_infra.run_drfs \"$@\""
python -m scagdrfs_infra.run_drfs "$@"
