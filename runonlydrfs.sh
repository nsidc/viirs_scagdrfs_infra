#!/bin/bash

# From Robyn Slack 3/25:  . ./tasks/run-drfs.sh -h /scratch/alpine/roma8902/scagdrfs/working/2026.03.09/h09v05/MOD09GA.A2026068.h09v05.061.2026069014006.NRT.hdf -w /scratch/alpine/roma8902/scagdrfs/working/2026.03.09/h09v05 -s /pl/active/daac-production/scagdrfs/staging -c /pl/active/daac-production/jpl_DRFS_Components/ How i can isolate and run drfs. This is when I am in /projects/roma8902/scagdrfs_infra with scag conda environment activated

# Note: changing scripts subdir from ./tasks to ./scripts

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

if [ ${use_python} -eq 1 ]; then
  echo "Changing dirs for use with python"
  workdir=${workdir}_py
  echo "workdir is now: $workdir"
  stagedir=${stagedir}_py
  echo "stagedir is now: $stagedir"
fi

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

# These are the files in the working directory after DRFS has run:
# These are the input files, and are expected to be there:
#   MOD09GA.A2026068.h09v05.061.2026069014006.NRT.hdf
#   MOD09GA.A2026068.h09v05.061.2026069014006.NRT.bip
#   MOD09GA.A2026068.h09v05.061.2026069014006.NRT.bip.meta

# These are created by hdf_solar():
#   MOD09GA.A2026068.h09v05.061.2026069014006.NRT.SolarZenith_1.dat
#   MOD09GA.A2026068.h09v05.061.2026069014006.NRT.SolarAzimuth_1.dat
# ${datprefix}.${solar}.dat

# These are created by the mod_drfs_v_1_2() IDL code
#   MOD09GA.A2026068.h09v05.061.2026069014006.NRT.deltavis.dat
#   MOD09GA.A2026068.h09v05.061.2026069014006.NRT.forcing.dat
#   MOD09GA.A2026068.h09v05.061.2026069014006.NRT.drfs.grnsz.dat
#   MOD09GA.A2026068.h09v05.061.2026069014006.NRT.forcing.cleanse.dat
#   MOD09GA.A2026068.h09v05.061.2026069014006.NRT.deltavis.cleanse.dat
#   MOD09GA.A2026068.h09v05.061.2026069014006.NRT.drfs.grnsz.cleanse.dat
# ${datprefix}.${dat}.dat

# These are created (in python) by mask_drfs():
#   MODSCGDRF_NRT_DELTAVIS_h09v05_MOD09GANRT061_20260309_V01.1.bin.Unmask
#   MODSCGDRF_NRT_drfsGS_h09v05_MOD09GANRT061_20260309_V01.1.bin.Unmask
#   MODSCGDRF_NRT_RF_h09v05_MOD09GANRT061_20260309_V01.1.bin.Unmask
#   MODSCGDRF_NRT_DELTAVIS_h09v05_MOD09GANRT061_20260309_V01.1.bin.mask
#   MODSCGDRF_NRT_drfsGS_h09v05_MOD09GANRT061_20260309_V01.1.bin.mask
#   MODSCGDRF_NRT_RF_h09v05_MOD09GANRT061_20260309_V01.1.bin.mask
# ${prodname}_${drfsvar}_${tileproddatever}.bin.${mask}

# These are created (in python) by mask_tif():
#   MODSCGDRF_NRT_RF_h09v05_MOD09GANRT061_20260309_V01.1.Unmask.tif
#   MODSCGDRF_NRT_drfsGS_h09v05_MOD09GANRT061_20260309_V01.1.Unmask.tif
#   MODSCGDRF_NRT_DELTAVIS_h09v05_MOD09GANRT061_20260309_V01.1.Unmask.tif
#   MODSCGDRF_NRT_RF_h09v05_MOD09GANRT061_20260309_V01.1.tif
#   MODSCGDRF_NRT_DELTAVIS_h09v05_MOD09GANRT061_20260309_V01.1.tif
#   MODSCGDRF_NRT_drfsGS_h09v05_MOD09GANRT061_20260309_V01.1.tif
# ${prodname}_${drfsvar}_${tileproddatever}.${tifext}

# Filename components:
prodname=MODSCGDRF_NRT
prodsrc=MOD09GA
tileproddatever=h09v05_MOD09GANRT061_20260309_V01.1
datprefix=MOD09GA.A2026068.h09v05.061.2026069014006.NRT
dats=(deltavis forcing drfs.grnsz forcing.cleanse deltavis.cleanse drfs.grnsz.cleanse)
drfsvars=(drfsGS DELTAVIS RF)
solars=(SolarZenith_1 SolarAzimuth_1)

# Remove generated files
echo -n "Removing intermediate and output files..."
for solar in ${solars[@]}; do
  # echo $solar
  fn=${workdir}/${datprefix}.${solar}.dat
  rm -f $fn
done

for dat in ${dats[@]}; do
  # echo $dat
  fn=${workdir}/${datprefix}.${dat}.dat
  rm -f $fn
done

for mask in mask Unmask; do
  for drfsvar in ${drfsvars[@]}; do 
    #echo "$drfsvar $mask"
    # ${prodname}_${drfsvar}_${tileproddatever}.bin.${mask}
    fn=${workdir}/${prodname}_${drfsvar}_${tileproddatever}.bin.${mask}
    rm -f $fn
  done
done

for tifext in tif Unmask.tif; do
  for drfsvar in ${drfsvars[@]}; do 
    # echo "$drfsvar $tifext"
    fn=${workdir}/${prodname}_${drfsvar}_${tileproddatever}.${tifext}
    rm -f $fn
  done
done
  
echo "done"

if [ ${use_python} -eq 1 ]; then
  echo "Running Python DRFS for ${hdf_ffn}"
  workdir=${workdir}_py
  stagedir=${stagedir}_py
  python -m src.run_drfs_python \
    --src-file ${hdf_ffn} \
    --component-dir ${compsdir} \
    --working-dir ${workdir}
else
  if [ ! -d ${stagedir} ]; then
    echo "No such stagedir: ${stagedir}"
    echo "Perhaps you are running on a login node?"
    exit 1
  fi
  cmd=". ./scripts/run-drfs.sh -h ${hdf_ffn} -w ${workdir} -s ${stagedir} -c ${compsdir}"
  echo "Running IDL DRFS:"
  echo "${cmd}"
  ${cmd}
fi
