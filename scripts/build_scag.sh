#!/bin/bash

# TODO: Rename this from clone_and_build.sh to build_scag.sh

# This replaces the call to env.sh
# source ${PWD}/config/env.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export TOPDIR="$(dirname "${SCRIPT_DIR}")"

# Get the scag repository
export SCAG_DIR=${TOPDIR}/scag_code

# Set environment variables and build executables
echo "Building scag executables..."
cd ${SCAG_DIR}
make build-alpine

cd $TOPDIR

echo
echo "...Finished building scag executables"
echo
