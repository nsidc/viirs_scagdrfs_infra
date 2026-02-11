#!/bin/bash

# Get the scag and scagdrfs_jpl repositories
echo "Cloning github repositories..."
source ${PWD}/tasks/clone.sh
echo "...done"
echo

# Set environment variables and build executables
echo "Building executables in repositories..."
source ${PWD}/tasks/build.sh
echo "...done"
echo

# Confirm ability to activate "scag" conda env
echo "Confirming scag conda environment..."
source ${PWD}/tasks/activate-scag-conda.sh
echo "Deactivating scag conda environment."
conda deactivate
echo "...done"
echo

# Create batch files needed for subprocess invocation of IDL
echo "Create idl startup batch file with local info..."
source ${PWD}/config/env.sh
# Create startup script for cmdline call of IDL
source ${PWD}/tasks/gen_drfs_idl_startup.sh ${PWD}/tasks/drfs_idl_startup.bat
echo "...done"
echo
