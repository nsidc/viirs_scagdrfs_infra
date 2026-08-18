#!/bin/bash

# convert2geotiffs.sh
#
# Convert existing ancillary files to geotiffs

echo "changing dir to one above this one so in root dir"
cd ..

ancroot=/pl/active/daac-production/viirsscgdrf_ancillary_v0
verstr=_v0

# Test files
tileIDs=(h13v01 h09v05 h29v13)

# All tiles with MODSCGDRF ancillary:
tileIDs=(h07v03 h08v03 h08v04 h08v05 h09v02 h09v03 h09v04 h09v05 h10v02 h10v03 h10v04 h10v05 h10v09 h10v10 h11v02 h11v03 h11v04 h11v05 h11v10 h11v11 h11v12 h12v01 h12v02 h12v03 h12v04 h12v05 h12v11 h12v12 h12v13 h13v01 h13v02 h13v03 h13v04 h13v13 h13v14 h14v01 h14v02 h14v03 h14v04 h14v09 h14v10 h14v11 h14v14 h15v02 h17v04 h18v04 h19v04 h22v04 h22v05 h23v04 h23v05 h23v06 h24v04 h24v05 h24v06 h25v04 h25v05 h25v06 h26v04 h26v05 h26v06 h27v04 h27v05 h27v06 h29v13 h30v13 h31v12 h31v13 h32v12)

anc_types=(aspect elevation slope waterpercentage)

echo "tileIDs..."
for tileID in "${tileIDs[@]}"; do
  echo "tileID: $tileID"

  # Because different ancillary files have differet dtypes,
  #   run each one individually
  
  # Aspect: float32
  asp_dir=${ancroot}/aspect
  dat_fn=${asp_dir}/aspect_${tileID}${verstr}.dat
  tif_fn=${asp_dir}/aspect_${tileID}${verstr}.tif
  python -m src.make_tif $dat_fn $tif_fn ${tileID} 2400 2400 float32 -9999
  echo "  Wrote tif file:  $tif_fn"

  # Elevation: int16
  ele_dir=${ancroot}/elevation
  dat_fn=${ele_dir}/elevation_${tileID}${verstr}.dat
  tif_fn=${ele_dir}/elevation_${tileID}${verstr}.tif
  python -m src.make_tif $dat_fn $tif_fn ${tileID} 2400 2400 uint16 65535
  echo "  Wrote tif file:  $tif_fn"

  # Slope: float32
  slp_dir=${ancroot}/slope
  dat_fn=${slp_dir}/slope_${tileID}${verstr}.dat
  tif_fn=${slp_dir}/slope_${tileID}${verstr}.tif
  python -m src.make_tif $dat_fn $tif_fn ${tileID} 2400 2400 float32 -9999
  echo "  Wrote tif file:  $tif_fn"

  # Water percentage: uint8
  wat_dir=${ancroot}/waterpercentage
  dat_fn=${wat_dir}/waterpercentage_${tileID}${verstr}.dat
  tif_fn=${wat_dir}/waterpercentage_${tileID}${verstr}.tif
  python -m src.make_tif $dat_fn $tif_fn ${tileID} 2400 2400 uint8 255
  echo "  Wrote tif file:  $tif_fn"

done
