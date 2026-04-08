""" Replaces scagdrfs_jpl's IDL file drfs_hdf_solar.pro

Input:
    in_file:  for MOD09GA, this is a .hdf file

Output:
    output is two binary files, extracted from the HDF fields:
        SolarZenith_1
        SolarAzimuth_1

    These are saved to files of template:
      strcompress(begin_name + sd_name[0] + '.dat' , /remove)
    which is:
      <orig_hdf_stem><varname>.dat
        (note: orig includes the directory name)
    eg
      .../h09v05/MOD09GA.A2026068.h09v05.061.2026069014006.NRT.hdf
    yields
      .../h09v05/MOD09GA.A2026068.h09v05.061.2026069014006.NRT.SolarAzimuth_1.dat
      .../h09v05/MOD09GA.A2026068.h09v05.061.2026069014006.NRT.SolarZenith_1.dat

Note: For MOD09GA, these fields are 1200x1200, but need to be saved as 2400x2400
  The IDL code does this by block-rebinning the fields using congrid
"""

import numpy as np
#import xarray as xr
from netCDF4 import Dataset


def extract_hdf_solar_fields(hdf_filename: str):
    """This replaces IDL "pro" drfs_hdf_solar() in drfs_hdf_solar.pro"""
    hdf_base_dirandfilename = hdf_filename.replace('.hdf', '')

    solar_hdf_varnames = [
        'SolarZenith_1',
        'SolarAzimuth_1',
    ]

    # xarray needs to use engine 'netcdf4' to open old-hdf(eos?) files
    # xarray will probably want to use engine "h5netcdf" for HDF5 files (like VIIRS)
    # ds = xr.open_dataset(hdf_filename, engine='netcdf4')
    ds = Dataset(hdf_filename)
    ds.set_auto_maskandscale(False)

    hdf_arrs = {}
    for hdf_varname in solar_hdf_varnames:
        hdf_arr = np.array(ds.variables[hdf_varname])
        print(f'hdf_arr {hdf_varname} is dtype: {hdf_arr.dtype=}')
        breakpoint()

        if hdf_arr.shape == (1200, 1200):
            print(f'Rescaling hdf_var {hdf_varname} by block-rebinning')

            hdf_arr_500m = np.zeros((2400, 2400), dtype=hdf_arr.dtype)
            for joff in range(2):
                for ioff in range(2):
                    hdf_arr_500m[joff::2, ioff::2] = hdf_arr[:, :]

            hdf_arrs[hdf_varname] = hdf_arr_500m
        elif hdf_arr.shape == (2400, 2400):
            hdf_arrs[hdf_varname] = hdf_arr
        else:
            raise ValueError(f'Expected hdf var {hdf_varname} to be 1200x1200 or 2400x2400')

    # Here, we should have:
    #  hdf_arrs['Solar_Zenith_1']
    #  hdf_arrs['Solar_Azimuth_1']
    #  ...which we can save

    for hdf_varname in solar_hdf_varnames:
        solar_dat_output_filename = hdf_base_dirandfilename + '.' + hdf_varname + '.dat'
        #print(f'is this right: {output_filename=}')

        hdf_arrs[hdf_varname].tofile(solar_dat_output_filename)
        print(f'  Wrote: {solar_dat_output_filename}')


if __name__ == '__main__':
    import sys

    ifn = sys.argv[1]

    extract_hdf_solar_fields(ifn)

    print(f'Finished running:\n  {sys.argv}')
