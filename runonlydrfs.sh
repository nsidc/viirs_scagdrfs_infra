#!/bin/bash

# From Robyn Slack 3/25:  . ./tasks/run-drfs.sh -h /scratch/alpine/roma8902/scagdrfs/working/2026.03.09/h09v05/MOD09GA.A2026068.h09v05.061.2026069014006.NRT.hdf -w /scratch/alpine/roma8902/scagdrfs/working/2026.03.09/h09v05 -s /pl/active/daac-production/scagdrfs/staging -c /pl/active/daac-production/jpl_DRFS_Components/ How i can isolate and run drfs. This is when I am in /projects/roma8902/scagdrfs_infra with scag conda environment activated


#operator_username=scotts
#operator_username=$(whoami)
operator_username=$USER
dotdate=2026.03.09
tileid=h09v05

# workdir: /scratch/alpine/roma8902/scagdrfs/working/2026.03.09/h09v05
workdir=/scratch/alpine/${operator_username}/scagdrfs/working/${dotdate}/${tileid}
hdf_bfn=MOD09GA.A2026068.h09v05.061.2026069014006.NRT.hdf
hdf_ffn=${workdir}/${hdf_bfn}

# TODO: Do these dirnames require the trailing slash?
stagedir=/pl/active/daac-production/scagdrfs/staging
compsdir=/pl/active/daac-production/jpl_DRFS_Components

# Check for existence of directories
if [ ! -d ${workdir} ]; then
  echo "No such workdir: ${workdir}"
  exit
fi

if [ ! -d ${stagedir} ]; then
  echo "No such stagedir: ${stagedir}"
  echo "Perhaps you are running in an interactive node?"
  exit
fi

if [ ! -d ${compsdir} ]; then
  echo "No such compsdir: ${compsdir}"
  exit
fi

# Check for existence input file (hdf for MODIS)
if [ ! -f ${hdf_ffn} ]; then
  echo "No such input file: ${hdf_ffn}"
  exit
fi

cmd=". ./scripts/run-drfs.sh -h ${hdf_ffn} -w ${workdir} -s ${stagedir} -c ${compsdir}"
echo "Executing command:"
echo "$cmd"

. ./scripts/run-drfs.sh -h ${hdf_ffn} -w ${workdir} -s ${stagedir} -c ${compsdir}
