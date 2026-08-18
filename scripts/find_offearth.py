"""Find where grid cells in modsinu tiles are off-earth

The approach is:
    Load the existing water-percentage file,
    Determine if there are off-earth (val = 253) grid cells
    if so, loop through existing modis data files and find where
      there is never any data.

Usage:
    python scripts/find_offearth.py
"""
import numpy as np
import glob
import re
from netCDF4 import Dataset
import os


def find_is_on_earth(tileid):
    """Find where there are values on earth for this tile"""
    modis_dir = '/pl/active/daac-production/MOD09GA/NRT'
    file_list = glob.glob(
        f'{modis_dir}/2025.*/MOD09GA.*.{tileid}.061*.hdf')
    print(f'  n_files {tileid}: {len(file_list)}')
    # print(f'  {file_list}')
    files_checked = {}
    tile_off_earth = None

    # for fn in file_list:
    for fn in file_list[:10]:
        bfn = os.path.basename(fn)
        if bfn in files_checked.keys():
            print('Duplicated: {fn}')
        else:
            files_checked[bfn] = True

        ds = Dataset(fn)
        ds.set_auto_maskandscale(False)
        n_obs = np.asarray(ds.variables['num_observations_500m'])
        is_off_earth = n_obs < 0
        if tile_off_earth is None:
            tile_off_earth = is_off_earth
        else:
            if np.all(tile_off_earth == is_off_earth):
                # print('match...')
                print('.', end='', flush=True)
            else:
                print('MISMATCH')
                breakpoint()

    return tile_off_earth


def find_offearth_values():
    """Find modsinu grid cells with off earth values"""
    watperc_dir = \
        '/pl/active/daac-production/viirsscgdrf_ancillary_v0/waterpercentage'

    print(f'Looking in: {watperc_dir}')
    all_waterperc_files = \
        glob.glob(f'{watperc_dir}/waterpercentage_h??v??*.dat')
    for wpfn in all_waterperc_files:
        # print(f'Checking: {wpfn}')
        watperc = np.fromfile(wpfn, dtype=np.uint8).reshape(2400, 2400)
        has_offearth = np.any(watperc == 253)
        tileid = re.search('h\d\dv\d\d', wpfn)[0]  # noqa
        if has_offearth:
            print(f'  Has offearth: {tileid} {wpfn}')
            is_off_earth = find_is_on_earth(tileid)
            ofn = f'offearth_{tileid}.dat'
            is_off_earth.tofile(ofn)
            print(f'Wrote: {ofn}')


if __name__ == '__main__':
    find_offearth_values()
