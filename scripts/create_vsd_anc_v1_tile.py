"""Create ancillary files for VIIRS scag drfs version 1

Usage:
    python -m scripts.create_vsd_anc_v1_tile <all|tileid>

  eg for all the tiles:
    python -m scripts.create_vsd_anc_v1_tile all
  or for a single tile
    python -m scripts.create_vsd_anc_v1_tile h13v01

Note: (note the line splitting here)
    non-tile-based ancillary files were copied from v0 to v1 with:
      cp -arv MODIS.wvl irrad10nm.wvl irradiance_arrays/
              ndgsi_LUTs/ spectral_libraries/
        ../viirsscgdrf_ancillary_v1/
"""

# import numpy as np
import os
import glob
import re
import numpy as np
from src.make_tif import write_geotiff_via_gdal


VERSTR = '_v1'
OUTPUT_ROOTDIR = f'/pl/active/daac-production/viirsscgdrf_ancillary{VERSTR}'


def get_all_tiles():
    """Return a list of all the tiles to create"""
    reference_dir = '/pl/active/daac-production/' \
        'viirsscgdrf_ancillary_srcfiles/GMTED20101_Output'
    if not os.path.isdir(reference_dir):
        print(f'No such dir: {reference_dir}')
        raise RuntimeError()

    print('Determining tiles from files in: {reference_dir}')
    all_tiles = []
    tile_dirs = glob.glob(f'{reference_dir}/h??v??')
    for tile_dir in tile_dirs:
        tileid = re.search(r'h\d\dv\d\d', tile_dir)[0]
        # print(f'tileid: {tileid}')
        all_tiles.append(tileid)

    return all_tiles


def create_vsd_anc(tileid):
    """Create all tile-dependent input files for this tileid"""
    print(f'Creating {VERSTR} ancillary files for: {tileid}')
    anc_srcdir = '/pl/active/daac-production/viirsscgdrf_ancillary_srcfiles'

    # water percentage info from MOD44
    #  Typical: mod44w_500m_h00v08.dat
    fn_wm500 = f'{anc_srcdir}/mod44w_500m/mod44w_500m_{tileid}.dat'
    wm500 = np.fromfile(fn_wm500, dtype=np.uint8).reshape(2400, 2400)
    is_offgrid = wm500 > 100

    # See if there is an offearth grid, which was created by examining
    #  where n_obs = -1 in MOD09GA files
    fn_offearth = f'{anc_srcdir}/offearth/offearth_{tileid}.dat'
    if os.path.isfile(fn_offearth):
        offearth = np.fromfile(fn_offearth, dtype=np.uint8).reshape(2400, 2400)
        num_offearth = np.sum(np.where(offearth == 1, 1, 0))
        print(f'  {tileid}: {num_offearth} off earth grid cells')
        is_offgrid = is_offgrid | (offearth == 1)

    # Now, we have enough to write the water percentage file
    dn_waterperc = f'{OUTPUT_ROOTDIR}/waterpercentage'
    os.makedirs(dn_waterperc, exist_ok=True)
    fn_waterperc = f'{dn_waterperc}/waterpercentage_{tileid}{VERSTR}.tif'
    waterperc = wm500.copy()
    waterperc[is_offgrid] = 253
    write_geotiff_via_gdal(
        fn_waterperc,
        waterperc,
        modsinu_tile=tileid,
        nodata_value=235,
    )
    print(f'  Wrote: {fn_waterperc}')

    # Generate slope and aspect files
    fn_slopeaspect = f'{anc_srcdir}/GMTED2010_Output/' \
        f'{tileid}/{tileid}_500m_slope_aspect.bsq'
    data_slope_aspect = np.fromfile(
        fn_slopeaspect,
        dtype=np.float32
    ).reshape(2, 2400, 2400)

    slope = data_slope_aspect[0, :, :]
    aspect = data_slope_aspect[1, :, :]

    slope.tofile('v1_slope.dat')
    aspect.tofile('v1_aspect.dat')

    fn_slopeaspect = f'{anc_srcdir}/GMTED2010_Output/' \
        f'{tileid}/{tileid}_500m_slope_aspect.bsq'

    # Slope values do not need any modification
    dn_slope = f'{OUTPUT_ROOTDIR}/slope'
    os.makedirs(dn_slope, exist_ok=True)
    fn_slope = f'{dn_slope}/slope_{tileid}{VERSTR}.tif'
    write_geotiff_via_gdal(
        fn_slope,
        slope,
        modsinu_tile=tileid,
        nodata_value=-999,
    )
    print(f'  Wrote: {fn_slope}')

    # Aspect values are -9999 if flat; set to 180
    aspect[aspect < -400] = 180

    dn_aspect = f'{OUTPUT_ROOTDIR}/aspect'
    os.makedirs(dn_aspect, exist_ok=True)
    fn_aspect = f'{dn_aspect}/aspect_{tileid}{VERSTR}.tif'
    write_geotiff_via_gdal(
        fn_aspect,
        aspect,
        modsinu_tile=tileid,
        nodata_value=-999,
    )
    print(f'  Wrote: {fn_aspect}')

    # Elvation file values are unchanged
    fn_elevation_input = f'{anc_srcdir}/GMTED2010_Output/' \
        f'{tileid}/{tileid}_500m_elevation.bsq'
    elevation = np.fromfile(
        fn_elevation_input, dtype=np.uint16).reshape(2400, 2400)
    dn_elevation = f'{OUTPUT_ROOTDIR}/elevation'
    os.makedirs(dn_elevation, exist_ok=True)
    fn_elevation = f'{dn_elevation}/elevation_{tileid}{VERSTR}.tif'
    write_geotiff_via_gdal(
        fn_elevation,
        elevation,
        modsinu_tile=tileid,
        nodata_value=65535,
    )
    print(f'  Wrote: {fn_elevation}')


if __name__ == '__main__':
    import sys

    if sys.argv[1] == 'all':
        all_tiles = get_all_tiles()
        print(f'Found {len(all_tiles)} tiles')
        for tileid in all_tiles:
            create_vsd_anc(tileid)
    else:
        tileid = sys.argv[1]
        create_vsd_anc(tileid)
