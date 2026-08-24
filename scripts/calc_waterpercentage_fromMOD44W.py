"""Use data in MOD44W files to calculate a 500m modsinu water percentage
This code assumes that you have downloaded a set of MOD44W data to a directory
  MOD44W files are .hdf with filenames, such as:
    MOD44W.A2025001.h18v03.061.2026042171001.hdf 

The code will loop through all of the files in that directory -- by default
  this is given in the global variables MOD44W_DIR.

The outputs are raw binary files: 2400x2400 ubyte
  Typical output file name:
      mod44w_500m_<tileID>.dat
    eg:
      mod44w_500m_h00v08.dat

The 'water_mask' field of the MOD44 input files is a 250m field (4800x4800)
  binary mask of 0 for nonwater, 1 for water, 250 for off-grid.

This code computes a simple average of the four underlying 250m grid cells
  for each 500m grid cell, and at the edge of the earth, does not count
  off-earth 250m cells in the denominator.

This code was developed using the 318 files from 2025 for MOD44W downloaded
  using EarthDataSearth, with file names:
    MOD44W.A2025001.<tileID>.061.*.hdf 

Usage:
    python calc_waterpercentage_fromMOD44.py
"""

import glob
import numpy as np
import re
from netCDF4 import Dataset
import os


MOD44W_DIR = './MOD44W_2025'
OUTPUT_DIR = './mod44w_500m'


def write_wp500(tileid, dname=MOD44W_DIR, outdir=OUTPUT_DIR):
    """Write the 500m water percentage field for this tile"""
    # print(f'tile: {tileid}')
    os.makedirs(outdir, exist_ok=True)

    fn_mod44 = glob.glob(f'{dname}/MOD44W.A*.{tileid}.*.hdf')[0]
    ds = Dataset(fn_mod44)
    wm250 = np.asarray(ds.variables['water_mask'])
    num_wm500 = np.zeros((2400, 2400), dtype=np.uint8)
    sum_wm500 = np.zeros((2400, 2400), dtype=np.uint8)
    for joff in range(2):
        for ioff in range(2):
            # is_valid = wm250[joff::2, ioff::2] <= 1
            subset = wm250[joff::2, ioff::2]
            is_sub_0 = subset == 0
            is_sub_1 = subset == 1
            is_sub_no = subset == 250
            assert np.all(is_sub_0 | is_sub_1 | is_sub_no)

            num_wm500[is_sub_0 | is_sub_1] += 1
            sum_wm500[is_sub_1] += 1

    is_valid_500m = num_wm500 > 0
    num_equals_1 = num_wm500 == 1
    num_equals_2 = num_wm500 == 2
    num_equals_3 = num_wm500 == 3
    sum_equals_1 = sum_wm500 == 1
    sum_equals_2 = sum_wm500 == 2
    sum_equals_3 = sum_wm500 == 3

    wm500 = np.full((2400, 2400), 255, dtype=np.uint8)

    wm500[(sum_wm500 == 0) & is_valid_500m] = 0

    wm500[sum_wm500 == 4] = 100

    wm500[sum_equals_1] = 25
    wm500[sum_equals_1 & num_equals_1] = 100
    wm500[sum_equals_1 & num_equals_2] = 50
    wm500[sum_equals_1 & num_equals_3] = 33

    wm500[sum_equals_2] = 50
    wm500[sum_equals_2 & num_equals_2] = 100
    wm500[sum_equals_2 & num_equals_3] = 67

    wm500[sum_equals_3] = 75
    wm500[sum_equals_3 & num_equals_3] = 100

    wm500[num_wm500 == 0] = 250

    # Typical output file name:
    #   mod44w_500m_h13v01.dat
    ofn = f'{outdir}/mod44w_500m_{tileid}.dat'
    wm500.tofile(ofn)
    print(f'  Wrote: {ofn}')


def get_list_of_all_tiles(dname=MOD44W_DIR):
    """Return a list of all the tiles"""
    # Typical file name:
    #  MOD44W.A2025001.h18v03.061.2026042171001.hdf 
    hdf_flist = glob.glob(f'{dname}/MOD44W.A*.hdf')
    tile_list = []
    for fn_hdf in hdf_flist:
        tileid = re.search(r'h\d\dv\d\d', fn_hdf)[0]
        # print(f'  tileid: {tileid}')
        tile_list.append(tileid)

    print(f'Found: {len(tile_list)} tiles in {dname}')
    return tile_list


if __name__ == '__main__':
    # Test a single tile
    # write_wp500('h29v13')
    # exit(0)

    tile_list = get_list_of_all_tiles()
    for tileid in tile_list:
        write_wp500(tileid)
