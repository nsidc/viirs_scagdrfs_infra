#!/usr/bin/env bash
# VIIRS SCAGDRFS environment configuration

# Project root (relative to this script's location)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export TOPDIR="$(dirname "${SCRIPT_DIR}")"

# PetaLibrary paths
export PETALIB_DIR=/pl/active/daac-production
export PETALIB_STAGING_DIR=/pl/active/daac-production/scagdrfs/staging

# VIIRS data paths
export VJ109GA_NRT_DIR=${PETALIB_DIR}/VJ109GA/NRT

# Working directories
export WORK_DIR=/scratch/alpine/${USER}/viirs_scagdrfs/working

# Python configuration - FIX THIS LINE
export PYTHONPATH="${TOPDIR}${PYTHONPATH:+:${PYTHONPATH}}"
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
