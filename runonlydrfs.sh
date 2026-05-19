#!/bin/bash

# From Robyn Slack 3/25:  . ./tasks/run-drfs.sh -h /scratch/alpine/roma8902/scagdrfs/working/2026.03.09/h09v05/MOD09GA.A2026068.h09v05.061.2026069014006.NRT.hdf -w /scratch/alpine/roma8902/scagdrfs/working/2026.03.09/h09v05 -s /pl/active/daac-production/scagdrfs/staging -c /pl/active/daac-production/jpl_DRFS_Components/ How i can isolate and run drfs. This is when I am in /projects/roma8902/scagdrfs_infra with scag conda environment activated

# Isolate and run DRFS for a single tile/date for testing and validation.
# Run from /projects/$USER/viirs_scagdrfs_infra with the viirs conda environment activated.
#
# Usage:
#   ./runonlydrfs.sh              # run IDL DRFS (default)
#   ./runonlydrfs.sh --python     # run Python DRFS

operator_username=$USER
dotdate=2026.03.09
tileid=h09v05
product=MOD09GA

# workdir=/scratch/alpine/${operator_username}/scagdrfs/working/${dotdate}/${tileid}
workdir=/scratch/alpine/${operator_username}/scagdrfs/working/${product}/${dotdate}/${tileid}
hdf_bfn=MOD09GA.A2026068.h09v05.061.2026069014006.NRT.hdf
hdf_ffn=${workdir}/${hdf_bfn}

stagedir=/pl/active/daac-production/scagdrfs/staging
compsdir=/pl/active/daac-production/jpl_DRFS_Components/

# Parse arguments
use_python=0
for arg in "$@"; do
  case $arg in
    --python) use_python=1 ;;
    *) echo "Unknown argument: $arg"; exit 1 ;;
  esac
done

# Check for existence of directories and input file
if [ ! -d ${workdir} ]; then
  echo "No such workdir: ${workdir}"
  exit 1
fi

if [ ! -d ${compsdir} ]; then
  echo "No such compsdir: ${compsdir}"
  exit 1
fi

if [ ! -f ${hdf_ffn} ]; then
  echo "No such input file: ${hdf_ffn}"
  exit 1
fi

if [ ${use_python} -eq 1 ]; then
  echo "Running Python DRFS for ${hdf_ffn}"
  python -m src.run_drfs_python \
    --src-file ${hdf_ffn} \
    --component-dir ${compsdir} \
    --working-dir ${workdir}
else
  if [ ! -d ${stagedir} ]; then
    echo "No such stagedir: ${stagedir}"
    echo "Perhaps you are running on an interactive node?"
    exit 1
  fi
  cmd=". ./scripts/run-drfs.sh -h ${hdf_ffn} -w ${workdir} -s ${stagedir} -c ${compsdir}"
  echo "Running IDL DRFS:"
  echo "${cmd}"
  ${cmd}
fi
