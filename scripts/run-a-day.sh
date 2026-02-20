#!/bin/bash

source ${PWD}/config/env.sh
#source ${PWD}/tasks/activate-scag-conda.sh
python -m src.run_a_day "$@"
