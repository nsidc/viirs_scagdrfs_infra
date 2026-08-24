#!/bin/bash

# create_unified_ancdir.sh
#
# move all ancillary files to a single directory structure
#
# eventually, the root directory will be our perma-directory
# dstroot=/pl/active/daac-production
dstroot=/scratch/alpine/scotts

ancdirname=viirsscgdrf_ancillary_v0
ancroot=${dstroot}/${ancdirname}

verstr=_v0
echo "Creating/copying ${verstr} files to: ${ancroot}"

# Copy existing files to "orig" subdirs
for ancdir in elevation slope aspect waterpercentage; do
  ancdir=${ancroot}/${ancdir}
  mkdir -p ${ancdir}
done

######################

# Copy the original files for: elevation
eledir=${ancroot}/elevation/
mkdir -p ${eledir}

slpdir=${ancroot}/slope/
mkdir -p ${slpdir}

aspdir=${ancroot}/aspect/
mkdir -p ${aspdir}

watdir=${ancroot}/waterpercentage/
mkdir -p ${watdir}

srcorig=/pl/active/daac-production/jpl_DRFS_Components/DEM
watdir_orig=/pl/active/daac-production/post_process_watermasks

# dem_30ARC_E60N90_RIGOROUS
for fn in ${srcorig}/dem_30ARC_E60N90_RIGOROUS_*.bsq; do
  bfn=$(basename $fn)
  tileID=${bfn:26:6}
  echo "30ARC: ${tileID}"

  # Note: verstr already has leading underscore (if defined)
  bfn_new="elevation_${tileID}${verstr}.dat"
  ffn_new=${eledir}/${bfn_new}
  if [ ! -f $ffn_new ]; then
    cp -av $fn ${ffn_new}
  fi

  # Split the slope and aspect files
  fn_slpasp=${fn/dem/terrain}
  fn_slp=${slpdir}/slope_${tileID}${verstr}.dat
  fn_asp=${aspdir}/aspect_${tileID}${verstr}.dat

  if [ ! -f $fn_slp ]; then
    if [ ! -f $fn_asp ]; then
      echo "  python separate_slope_aspect.py $fn_slpasp $fn_slp $fn_asp"
      python separate_slope_aspect.py $fn_slpasp $fn_slp $fn_asp
    fi
  fi
  
  # copy the water-percentage file
  fn_wat_old=$(ls ${watdir_orig}/MOD44W.A2000055.${tileID}.006.*.water_pcent.bin)
  fn_wat_new=${watdir}/waterpercentage_${tileID}${verstr}.dat
  if [ ! -f $fn_wat_new ]; then
    cp -av $fn_wat_old $fn_wat_new
  fi

done

echo

# dem_GTOPO30_NN_*.bsq
for fn in ${srcorig}/dem_GTOPO30_NN_*.bsq; do
  bfn=$(basename $fn)
  tileID=${bfn:15:6}
  echo "GTOPO30: ${tileID}"

  bfn_new="elevation_${tileID}${verstr}.dat"
  ffn_new=${eledir}/${bfn_new}
  if [ ! -f $ffn_new ]; then
    cp -av $fn ${ffn_new}
  fi
  
  # Split the slope and aspect files
  fn_slpasp=${fn/dem/terrain}
  fn_slp=${slpdir}/slope_${tileID}${verstr}.dat
  fn_asp=${aspdir}/aspect_${tileID}${verstr}.dat

  if [ ! -f $fn_slp ]; then
    if [ ! -f $fn_asp ]; then
      echo "  python separate_slope_aspect.py $fn_slpasp $fn_slp $fn_asp"
      python separate_slope_aspect.py $fn_slpasp $fn_slp $fn_asp
    fi
  fi
  
  # copy the water-percentage file
  fn_wat_old=$(ls ${watdir_orig}/MOD44W.A2000055.${tileID}.006.*.water_pcent.bin)
  fn_wat_new=${watdir}/waterpercentage_${tileID}${verstr}.dat
  if [ ! -f $fn_wat_new ]; then
    cp -av $fn_wat_old $fn_wat_new
  fi

done

echo
# dem_gmted_med075_*.bsq
for fn in ${srcorig}/dem_gmted_med075*.bsq; do
  bfn=$(basename $fn)
  tileID=${bfn:17:6}
  echo "gmted: ${tileID}"

  bfn_new="elevation_${tileID}${verstr}.dat"
  ffn_new=${eledir}/${bfn_new}
  if [ ! -f $ffn_new ]; then
    cp -av $fn ${ffn_new}
  fi

  # Split the slope and aspect files
  fn_slpasp=${fn/dem/terrain}
  fn_slp=${slpdir}/slope_${tileID}${verstr}.dat
  fn_asp=${aspdir}/aspect_${tileID}${verstr}.dat

  if [ ! -f $fn_slp ]; then
    if [ ! -f $fn_asp ]; then
      echo "  python separate_slope_aspect.py $fn_slpasp $fn_slp $fn_asp"
      python separate_slope_aspect.py $fn_slpasp $fn_slp $fn_asp
    fi
  fi
  
  # copy the water-percentage file
  fn_wat_old=$(ls ${watdir_orig}/MOD44W.A2000055.${tileID}.006.*.water_pcent.bin)
  fn_wat_new=${watdir}/waterpercentage_${tileID}${verstr}.dat
  if [ ! -f $fn_wat_new ]; then
    cp -av $fn_wat_old $fn_wat_new
  fi

done

echo "Finished copy/renaming files to:  $ancroot"
