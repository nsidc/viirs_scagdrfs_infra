#!/usr/bin/env bash
# VIIRS SCAGDRFS environment configuration

# Project root (relative to this script's location)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export TOPDIR="$(dirname "${SCRIPT_DIR}")"

# PetaLibrary paths
# Where the NRT files are grabbed from
export PETALIB_DIR=/pl/active/daac-production
# This is the one that is used for MODIS - commenting until we figure out what we want
# export PETALIB_STAGING_DIR=/pl/active/daac-production/scagdrfs/staging
# NOTE: This is temporary for while we are in development phase
export PETALIB_STAGING_DIR=/scratch/alpine/${USER}/viirs_scagdrfs/staging

# data paths
export VNP09GA_NRT_DIR=${PETALIB_DIR}/VNP09GA/NRT
export VJ109GA_NRT_DIR=${PETALIB_DIR}/VJ109GA/NRT
export MOD09GA_NRT_DIR=${PETALIB_DIR}/MOD09GA/NRT
export WATER_MASK_DIR=${PETALIB_DIR}/post_process_watermasks

# Working directories
export WORK_DIR=/scratch/alpine/${USER}/scagdrfs/working

# SCAG specific environment setup
export SCAG_DIR=${TOPDIR}/scag
export SCAG_CONFIG_DIR=${SCAG_DIR}/config

# DRFS specific environment setup
# TODO:  This is actively changing while drfs is implemented...
# NOTE:  The system and LD path were changed in scagdrfs_infra, but did not seem to be needed here
module load idl
export DRFS_DIR=${TOPDIR}/scagdrfs_jpl
export DRFS_IDL_DIR=${DRFS_DIR}/snowHydro
export DRFS_COMPONENT_DIR=/pl/active/daac-production/jpl_DRFS_Components/
export SCAGDRFS_CONSTANTS_DIR=${TOPDIR}/src/constants

# Python configuration - FIX THIS LINE
### TODO: This is probably not necessary.  Leaving it here until
###       that is confirmed
### export PYTHONPATH="${TOPDIR}${PYTHONPATH:+:${PYTHONPATH}}"
export CONSTANTS_DIR=${TOPDIR}/src/constants

# Create necessary directories
mkdir -p "${WORK_DIR}" 2>/dev/null || true
mkdir -p "${PETALIB_STAGING_DIR}" 2>/dev/null || true

# Logging (optional)
export LOG_LEVEL=${LOG_LEVEL:-INFO}
export LOG_DIR=${WORK_DIR}/logs
mkdir -p "${LOG_DIR}" 2>/dev/null || true

# Display configuration
if [[ "${VERBOSE:-0}" == "1" ]]; then
    echo "VIIRS SCAGDRFS environment loaded:"
    echo "  Top dir: ${TOPDIR}"
    echo "  Work dir: ${WORK_DIR}"
    echo "  VJ109GA NRT dir: ${VJ109GA_NRT_DIR}"
    echo "  PYTHONPATH: ${PYTHONPATH}"
fi
