#!/usr/bin/env bash
# Minimum shell environment — only what Python cannot do.

# Needed to build paths to IDL/SCAG tools used by shell scripts
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export TOPDIR="$(dirname "${SCRIPT_DIR}")"

export SCAG_DIR=${TOPDIR}/scag_code
# export SCAG_CONFIG_DIR=${SCAG_DIR}/config
# export DRFS_DIR=${TOPDIR}/scagdrfs_jpl
# export DRFS_IDL_DIR=${DRFS_DIR}/snowHydro

# Required to run IDL
# module load idl
