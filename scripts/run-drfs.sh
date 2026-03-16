#!/bin/bash

source ${PWD}/config/env.sh
source ${PWD}/tasks/activate-scag-conda.sh
python -m scagdrfs_infra.run_drfs "$@"
