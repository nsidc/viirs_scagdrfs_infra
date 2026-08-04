"""
modis_tile_ncattrs.py

Generate ncattrs by MODIS sinusoidal grid tileID

Usage:
    python modis_tile_ncattrs.py <tileID>

  where:
    tileID is of the form:
        hHHvVV  where h and v are the letters 'h' and 'v'
      or
        vVVhHH  where v and h are the letters 'v' and 'h'
      and in either case:
          HH is a zero-padded integer between 00 and 35
          VV is a zero-padded integer between 00 and 17

 eg
    python modis_tile_ncattrs.py h08v17
 or
    python modis_tile_ncattrs.py v17h08

Note: the code does not care if the tileID is given as:
    v..h..  <-- vertical index first
  or
    h..v..  <-- horizontal index first


=========
Examples:
=========

# Example of non-valid MODIS land tile:

  python modis_tile_ncattrs.py h07v17

yields ->

  h07v17 is not a valid MODIS land tile


# Example of valid MODIS land tile that is along left (westmost) edge of earth

  python modis_tile_ncattrs.py v02h11

yields ->

  tile indices of: v02h11
    horizontal index: 11
      vertical index: 02

    Projected extents:
       xmin:  -7783653.63762    xmax:  -6671703.11796
       ymin:   6671703.11796    ymax:   7783653.63762

    geospatial_lon_min: -180.0
    geospatial_lon_max: -119.9833

    geospatial_lat_min: 60.0
    geospatial_lat_max: 70.0

    geotransform_string:
       "-7783653.63762 463.312716525 0 7783653.63762 0 -463.312716525 "

    geospatial_bounds_str:
       POLYGON((60.0000 -180.0000,70.0000 -180.0000,70.0000 -119.9833,60.0000 -119.9833,60.0000 -180.0000))

"""

import sys
from src.constants.paths import CONSTANTS_DIR
# from constants.paths import CONSTANTS_DIR  # This version allows user to call file directly
from pathlib import Path
import pandas as pd
import yaml


# res500m = 463.312716524999985  # from geotiff of MOD09GA file
# res500m = 463.312716525        # as above, correcting float64 discretization
# res500m = 463.312716527778     # From typical VJ109GA file
# res500m = 463.31271656938424   # apparent GDAL value
res500m = 463.31271652777775     # This value yield exact results with MOD09GA 500m files


def get_tiletuple_from_arg(argstr):
    """Expects tileID of form vVVhHH or hHHvVV where VV is 00-17, HH is 00-35"""
    if argstr[0] == "h" and argstr[3] == "v":
        hID = int(argstr[1:3])
        vID = int(argstr[4:])
    elif argstr[0] == "v" and argstr[3] == "h":
        vID = int(argstr[1:3])
        hID = int(argstr[4:])
    else:
        raise ValueError(f"arg is not in form vVVhHH nor hHHvVV: {argstr}")

    try:
        assert 0 <= hID <= 35
    except AssertionError:
        raise ValueError(f"horizontal column out of range 0-35 for {argstr}: {hID}")

    try:
        assert 0 <= vID <= 17
    except AssertionError:
        raise ValueError(f"vertical row out of range 0-17 for {argstr}: {vID}")

    return (hID, vID)


def get_xy_minmax(hID, vID):
    """Return the xmin, xmax, ymax, ymin for this tile tuple"""

    xmin = (hID - 18) * res500m * 2400
    xmax = (hID - 18 + 1) * res500m * 2400
    ymax = (9 - vID) * res500m * 2400
    ymin = (9 - vID - 1) * res500m * 2400

    return xmin, xmax, ymin, ymax


def get_geotransform(hID, vID):
    """
    Return GeoTransform string for this tile tuple

    Note: GeoTransform is a string containing:
      "ULX dx 0 ULY 0 -dy "  <-- note the trailing space
    """
    xmin, _, _, ymax = get_xy_minmax(hID, vID)

    geotransform_string = f"{xmin:.5f} {res500m} 0 {ymax:.5f} 0 {-res500m} "

    return geotransform_string


def get_geospatial_bounds_xy(hID, vID):
    """Return the string containing the geospatial_bounds string
    which is a POLYGON statement in the projected coordinates"""

    xmin, xmax, ymin, ymax = get_xy_minmax(hID, vID)

    ulx, uly = xmin, ymax
    urx, ury = xmax, ymax
    lrx, lry = xmax, ymin
    llx, lly = xmin, ymin

    # geospatial_bounds_str is:
    #   POLYGON((ulx, uly), (urx, ury), (lrx, lry), (llx, lly), (ulx, uly))

    geospatial_bounds_str = f"POLYGON(({ulx:.4f} {uly:.4f}),({urx:.4f} {ury:.4f}),({lrx:.4f} {lry:.4f}),({llx:.4f} {lly:.4f}),({ulx:.4f} {uly:.4f}))"

    return geospatial_bounds_str


def get_geospatial_bounds_latlon(hID, vID):
    """
    Note: This version uses nominal 10-degree spacing along
           horizontal grid edges and 1-degree spacing along
           vertical grid edges with vertices added for the
           last-valid grid cell vertex at the -180/+180 degree
           longitude line.
    """
    gsbounds_filename = Path(CONSTANTS_DIR / 'modis_tile_geospatial_bounds.yml')
    with open(gsbounds_filename) as f:
        gs_bounds_dict = yaml.safe_load(f)
    tileID = f'h{hID:02d}v{vID:02d}'

    polygon_str = gs_bounds_dict[tileID]

    return polygon_str


def get_geospatial_bounds_latlon_v1(hID, vID):
    """
    Note: This version creates a trapezoid using the MODLAND min/max lat/lon values.
          but has been superseded by the new version which uses nominal 10-degree
          spacing along horizontal grid edges and 1-degree spacing along vertical
          grid edges with vertices added for the last-valid grid cell vertex at
          the -180/+180 degree longitude line.
    Return the string containing the geospatial_bounds string
    which is a POLYGON statement in the projected coordinates"""

    is_valid_tileID, lon_min, lon_max, lat_min, lat_max = look_up_latlon_minmax(
        hID, vID
    )

    # geospatial_bounds_str is of the form [note spaces between x,y and commas between points]:
    #   POLYGON((llx lly, ulx uly, urx ury, lrx lry, llx lly))
    # E.g. the example from ACDD-1.3 is:
    #   Example: 'POLYGON ((40.26 -111.29, 41.26 -111.29, 41.26 -110.29, 40.26 -110.29, 40.26 -111.29))'
    if is_valid_tileID:
        # For EPSG:4326, first coord is latitude, second is longitude
        # Points are: LL, UL, UR, UR, LR, LL(again)
        # Note: the original file from MODIS has four digits after decimal point
        geospatial_bounds_str = (
            "POLYGON(("
            f"{lat_min:.4f} {lon_min:.4f},"
            f"{lat_max:.4f} {lon_min:.4f},"
            f"{lat_max:.4f} {lon_max:.4f},"
            f"{lat_min:.4f} {lon_max:.4f},"
            f"{lat_min:.4f} {lon_min:.4f}"
            "))"
        )
    else:
        print(f"NOT A VALID MODIS TILE: h{hID:02d}v{vID:02d}")
        geospatial_bounds_str = ""

    return geospatial_bounds_str


def look_up_latlon_minmax(hID, vID):
    """Use values for min/max lat/lon calculated to replace
    the values found at:
         https://modis-land.gsfc.nasa.gov/pdf/sn_bound_10deg.txt
    """

    latlon_minmax_filename = Path(CONSTANTS_DIR / 'modis_tile_lonlat_bounds.txt')
    bounds = pd.read_csv(latlon_minmax_filename, sep='\s+')  # noqa

    lon_min = float(bounds[(bounds['ih'] == hID) & (bounds['iv'] == vID)]['lon_min'])
    lon_max = float(bounds[(bounds['ih'] == hID) & (bounds['iv'] == vID)]['lon_max'])
    lat_min = float(bounds[(bounds['ih'] == hID) & (bounds['iv'] == vID)]['lat_min'])
    lat_max = float(bounds[(bounds['ih'] == hID) & (bounds['iv'] == vID)]['lat_max'])

    is_valid_tileID = lon_min > -200

    return is_valid_tileID, lon_min, lon_max, lat_min, lat_max


def look_up_latlon_minmax_orig(hID, vID):
    """
    Note: This routine is superseded by the new routine, but left
       here for reference.
    Use the values in:
         https://modis-land.gsfc.nasa.gov/pdf/sn_bound_10deg.txt
    to provide the global ncattrs:
      geospatial_[lat|lon]_[min|max]

    Note: These values were cut-and-pasted from the above URL text file
          Then, values with all missing were deleted
          Then, the columns were organized so the data could be accessed via dictionary keys
    """

    lonlat_minmax = {
        0: {},
        1: {},
        2: {},
        3: {},
        4: {},
        5: {},
        6: {},
        7: {},
        8: {},
        9: {},
        10: {},
        11: {},
        12: {},
        13: {},
        14: {},
        15: {},
        16: {},
        17: {},
    }

    #             iv  ih        lon_min    lon_max   lat_min   lat_max
    lonlat_minmax[0][14] = (-180.0000, -172.7151, 80.0000, 80.4083)
    lonlat_minmax[0][15] = (-180.0000, -115.1274, 80.0000, 83.6250)
    lonlat_minmax[0][16] = (-180.0000, -57.5397, 80.0000, 86.8167)
    lonlat_minmax[0][17] = (-180.0000, 57.2957, 80.0000, 90.0000)
    lonlat_minmax[0][18] = (-0.0040, 180.0000, 80.0000, 90.0000)
    lonlat_minmax[0][19] = (57.5877, 180.0000, 80.0000, 86.8167)
    lonlat_minmax[0][20] = (115.1754, 180.0000, 80.0000, 83.6250)
    lonlat_minmax[0][21] = (172.7631, 180.0000, 80.0000, 80.4083)
    lonlat_minmax[1][11] = (-180.0000, -175.4039, 70.0000, 70.5333)
    lonlat_minmax[1][12] = (-180.0000, -146.1659, 70.0000, 73.8750)
    lonlat_minmax[1][13] = (-180.0000, -116.9278, 70.0000, 77.1667)
    lonlat_minmax[1][14] = (-180.0000, -87.6898, 70.0000, 80.0000)
    lonlat_minmax[1][15] = (-172.7631, -58.4517, 70.0000, 80.0000)
    lonlat_minmax[1][16] = (-115.1754, -29.2137, 70.0000, 80.0000)
    lonlat_minmax[1][17] = (-57.5877, 0.0480, 70.0000, 80.0000)
    lonlat_minmax[1][18] = (0.0000, 57.6357, 70.0000, 80.0000)
    lonlat_minmax[1][19] = (29.2380, 115.2234, 70.0000, 80.0000)
    lonlat_minmax[1][20] = (58.4761, 172.8111, 70.0000, 80.0000)
    lonlat_minmax[1][21] = (87.7141, 180.0000, 70.0000, 80.0000)
    lonlat_minmax[1][22] = (116.9522, 180.0000, 70.0000, 77.1583)
    lonlat_minmax[1][23] = (146.1902, 180.0000, 70.0000, 73.8750)
    lonlat_minmax[1][24] = (175.4283, 180.0000, 70.0000, 70.5333)
    lonlat_minmax[2][9] = (-180.0000, -159.9833, 60.0000, 63.6167)
    lonlat_minmax[2][10] = (-180.0000, -139.9833, 60.0000, 67.1167)
    lonlat_minmax[2][11] = (-180.0000, -119.9833, 60.0000, 70.0000)
    lonlat_minmax[2][12] = (-175.4283, -99.9833, 60.0000, 70.0000)
    lonlat_minmax[2][13] = (-146.1902, -79.9833, 60.0000, 70.0000)
    lonlat_minmax[2][14] = (-116.9522, -59.9833, 60.0000, 70.0000)
    lonlat_minmax[2][15] = (-87.7141, -39.9833, 60.0000, 70.0000)
    lonlat_minmax[2][16] = (-58.4761, -19.9833, 60.0000, 70.0000)
    lonlat_minmax[2][17] = (-29.2380, 0.0244, 60.0000, 70.0000)
    lonlat_minmax[2][18] = (0.0000, 29.2624, 60.0000, 70.0000)
    lonlat_minmax[2][19] = (20.0000, 58.5005, 60.0000, 70.0000)
    lonlat_minmax[2][20] = (40.0000, 87.7385, 60.0000, 70.0000)
    lonlat_minmax[2][21] = (60.0000, 116.9765, 60.0000, 70.0000)
    lonlat_minmax[2][22] = (80.0000, 146.2146, 60.0000, 70.0000)
    lonlat_minmax[2][23] = (100.0000, 175.4526, 60.0000, 70.0000)
    lonlat_minmax[2][24] = (120.0000, 180.0000, 60.0000, 70.0000)
    lonlat_minmax[2][25] = (140.0000, 180.0000, 60.0000, 67.1167)
    lonlat_minmax[2][26] = (160.0000, 180.0000, 60.0000, 63.6167)
    lonlat_minmax[3][6] = (-180.0000, -171.1167, 50.0000, 52.3333)
    lonlat_minmax[3][7] = (-180.0000, -155.5594, 50.0000, 56.2583)
    lonlat_minmax[3][8] = (-180.0000, -140.0022, 50.0000, 60.0000)
    lonlat_minmax[3][9] = (-180.0000, -124.4449, 50.0000, 60.0000)
    lonlat_minmax[3][10] = (-160.0000, -108.8877, 50.0000, 60.0000)
    lonlat_minmax[3][11] = (-140.0000, -93.3305, 50.0000, 60.0000)
    lonlat_minmax[3][12] = (-120.0000, -77.7732, 50.0000, 60.0000)
    lonlat_minmax[3][13] = (-100.0000, -62.2160, 50.0000, 60.0000)
    lonlat_minmax[3][14] = (-80.0000, -46.6588, 50.0000, 60.0000)
    lonlat_minmax[3][15] = (-60.0000, -31.1015, 50.0000, 60.0000)
    lonlat_minmax[3][16] = (-40.0000, -15.5443, 50.0000, 60.0000)
    lonlat_minmax[3][17] = (-20.0000, 0.0167, 50.0000, 60.0000)
    lonlat_minmax[3][18] = (0.0000, 20.0167, 50.0000, 60.0000)
    lonlat_minmax[3][19] = (15.5572, 40.0167, 50.0000, 60.0000)
    lonlat_minmax[3][20] = (31.1145, 60.0167, 50.0000, 60.0000)
    lonlat_minmax[3][21] = (46.6717, 80.0167, 50.0000, 60.0000)
    lonlat_minmax[3][22] = (62.2290, 100.0167, 50.0000, 60.0000)
    lonlat_minmax[3][23] = (77.7862, 120.0167, 50.0000, 60.0000)
    lonlat_minmax[3][24] = (93.3434, 140.0167, 50.0000, 60.0000)
    lonlat_minmax[3][25] = (108.9007, 160.0167, 50.0000, 60.0000)
    lonlat_minmax[3][26] = (124.4579, 180.0000, 50.0000, 60.0000)
    lonlat_minmax[3][27] = (140.0151, 180.0000, 50.0000, 60.0000)
    lonlat_minmax[3][28] = (155.5724, 180.0000, 50.0000, 56.2500)
    lonlat_minmax[3][29] = (171.1296, 180.0000, 50.0000, 52.3333)
    lonlat_minmax[4][4] = (-180.0000, -169.6921, 40.0000, 43.7667)
    lonlat_minmax[4][5] = (-180.0000, -156.6380, 40.0000, 48.1917)
    lonlat_minmax[4][6] = (-180.0000, -143.5839, 40.0000, 50.0000)
    lonlat_minmax[4][7] = (-171.1296, -130.5299, 40.0000, 50.0000)
    lonlat_minmax[4][8] = (-155.5724, -117.4758, 40.0000, 50.0000)
    lonlat_minmax[4][9] = (-140.0151, -104.4217, 40.0000, 50.0000)
    lonlat_minmax[4][10] = (-124.4579, -91.3676, 40.0000, 50.0000)
    lonlat_minmax[4][11] = (-108.9007, -78.3136, 40.0000, 50.0000)
    lonlat_minmax[4][12] = (-93.3434, -65.2595, 40.0000, 50.0000)
    lonlat_minmax[4][13] = (-77.7862, -52.2054, 40.0000, 50.0000)
    lonlat_minmax[4][14] = (-62.2290, -39.1513, 40.0000, 50.0000)
    lonlat_minmax[4][15] = (-46.6717, -26.0973, 40.0000, 50.0000)
    lonlat_minmax[4][16] = (-31.1145, -13.0432, 40.0000, 50.0000)
    lonlat_minmax[4][17] = (-15.5572, 0.0130, 40.0000, 50.0000)
    lonlat_minmax[4][18] = (0.0000, 15.5702, 40.0000, 50.0000)
    lonlat_minmax[4][19] = (13.0541, 31.1274, 40.0000, 50.0000)
    lonlat_minmax[4][20] = (26.1081, 46.6847, 40.0000, 50.0000)
    lonlat_minmax[4][21] = (39.1622, 62.2419, 40.0000, 50.0000)
    lonlat_minmax[4][22] = (52.2163, 77.7992, 40.0000, 50.0000)
    lonlat_minmax[4][23] = (65.2704, 93.3564, 40.0000, 50.0000)
    lonlat_minmax[4][24] = (78.3244, 108.9136, 40.0000, 50.0000)
    lonlat_minmax[4][25] = (91.3785, 124.4709, 40.0000, 50.0000)
    lonlat_minmax[4][26] = (104.4326, 140.0281, 40.0000, 50.0000)
    lonlat_minmax[4][27] = (117.4867, 155.5853, 40.0000, 50.0000)
    lonlat_minmax[4][28] = (130.5407, 171.1426, 40.0000, 50.0000)
    lonlat_minmax[4][29] = (143.5948, 180.0000, 40.0000, 50.0000)
    lonlat_minmax[4][30] = (156.6489, 180.0000, 40.0000, 48.1917)
    lonlat_minmax[4][31] = (169.7029, 180.0000, 40.0000, 43.7583)
    lonlat_minmax[5][2] = (-180.0000, -173.1955, 30.0000, 33.5583)
    lonlat_minmax[5][3] = (-180.0000, -161.6485, 30.0000, 38.9500)
    lonlat_minmax[5][4] = (-180.0000, -150.1014, 30.0000, 40.0000)
    lonlat_minmax[5][5] = (-169.7029, -138.5544, 30.0000, 40.0000)
    lonlat_minmax[5][6] = (-156.6489, -127.0074, 30.0000, 40.0000)
    lonlat_minmax[5][7] = (-143.5948, -115.4604, 30.0000, 40.0000)
    lonlat_minmax[5][8] = (-130.5407, -103.9134, 30.0000, 40.0000)
    lonlat_minmax[5][9] = (-117.4867, -92.3664, 30.0000, 40.0000)
    lonlat_minmax[5][10] = (-104.4326, -80.8194, 30.0000, 40.0000)
    lonlat_minmax[5][11] = (-91.3785, -69.2724, 30.0000, 40.0000)
    lonlat_minmax[5][12] = (-78.3244, -57.7254, 30.0000, 40.0000)
    lonlat_minmax[5][13] = (-65.2704, -46.1784, 30.0000, 40.0000)
    lonlat_minmax[5][14] = (-52.2163, -34.6314, 30.0000, 40.0000)
    lonlat_minmax[5][15] = (-39.1622, -23.0844, 30.0000, 40.0000)
    lonlat_minmax[5][16] = (-26.1081, -11.5374, 30.0000, 40.0000)
    lonlat_minmax[5][17] = (-13.0541, 0.0109, 30.0000, 40.0000)
    lonlat_minmax[5][18] = (0.0000, 13.0650, 30.0000, 40.0000)
    lonlat_minmax[5][19] = (11.5470, 26.1190, 30.0000, 40.0000)
    lonlat_minmax[5][20] = (23.0940, 39.1731, 30.0000, 40.0000)
    lonlat_minmax[5][21] = (34.6410, 52.2272, 30.0000, 40.0000)
    lonlat_minmax[5][22] = (46.1880, 65.2812, 30.0000, 40.0000)
    lonlat_minmax[5][23] = (57.7350, 78.3353, 30.0000, 40.0000)
    lonlat_minmax[5][24] = (69.2820, 91.3894, 30.0000, 40.0000)
    lonlat_minmax[5][25] = (80.8290, 104.4435, 30.0000, 40.0000)
    lonlat_minmax[5][26] = (92.3760, 117.4975, 30.0000, 40.0000)
    lonlat_minmax[5][27] = (103.9230, 130.5516, 30.0000, 40.0000)
    lonlat_minmax[5][28] = (115.4701, 143.6057, 30.0000, 40.0000)
    lonlat_minmax[5][29] = (127.0171, 156.6598, 30.0000, 40.0000)
    lonlat_minmax[5][30] = (138.5641, 169.7138, 30.0000, 40.0000)
    lonlat_minmax[5][31] = (150.1111, 180.0000, 30.0000, 40.0000)
    lonlat_minmax[5][32] = (161.6581, 180.0000, 30.0000, 38.9417)
    lonlat_minmax[5][33] = (173.2051, 180.0000, 30.0000, 33.5583)
    lonlat_minmax[6][1] = (-180.0000, -170.2596, 20.0000, 27.2667)
    lonlat_minmax[6][2] = (-180.0000, -159.6178, 20.0000, 30.0000)
    lonlat_minmax[6][3] = (-173.2051, -148.9760, 20.0000, 30.0000)
    lonlat_minmax[6][4] = (-161.6581, -138.3342, 20.0000, 30.0000)
    lonlat_minmax[6][5] = (-150.1111, -127.6925, 20.0000, 30.0000)
    lonlat_minmax[6][6] = (-138.5641, -117.0507, 20.0000, 30.0000)
    lonlat_minmax[6][7] = (-127.0171, -106.4089, 20.0000, 30.0000)
    lonlat_minmax[6][8] = (-115.4701, -95.7671, 20.0000, 30.0000)
    lonlat_minmax[6][9] = (-103.9230, -85.1254, 20.0000, 30.0000)
    lonlat_minmax[6][10] = (-92.3760, -74.4836, 20.0000, 30.0000)
    lonlat_minmax[6][11] = (-80.8290, -63.8418, 20.0000, 30.0000)
    lonlat_minmax[6][12] = (-69.2820, -53.2000, 20.0000, 30.0000)
    lonlat_minmax[6][13] = (-57.7350, -42.5582, 20.0000, 30.0000)
    lonlat_minmax[6][14] = (-46.1880, -31.9165, 20.0000, 30.0000)
    lonlat_minmax[6][15] = (-34.6410, -21.2747, 20.0000, 30.0000)
    lonlat_minmax[6][16] = (-23.0940, -10.6329, 20.0000, 30.0000)
    lonlat_minmax[6][17] = (-11.5470, 0.0096, 20.0000, 30.0000)
    lonlat_minmax[6][18] = (0.0000, 11.5566, 20.0000, 30.0000)
    lonlat_minmax[6][19] = (10.6418, 23.1036, 20.0000, 30.0000)
    lonlat_minmax[6][20] = (21.2836, 34.6506, 20.0000, 30.0000)
    lonlat_minmax[6][21] = (31.9253, 46.1976, 20.0000, 30.0000)
    lonlat_minmax[6][22] = (42.5671, 57.7446, 20.0000, 30.0000)
    lonlat_minmax[6][23] = (53.2089, 69.2917, 20.0000, 30.0000)
    lonlat_minmax[6][24] = (63.8507, 80.8387, 20.0000, 30.0000)
    lonlat_minmax[6][25] = (74.4924, 92.3857, 20.0000, 30.0000)
    lonlat_minmax[6][26] = (85.1342, 103.9327, 20.0000, 30.0000)
    lonlat_minmax[6][27] = (95.7760, 115.4797, 20.0000, 30.0000)
    lonlat_minmax[6][28] = (106.4178, 127.0267, 20.0000, 30.0000)
    lonlat_minmax[6][29] = (117.0596, 138.5737, 20.0000, 30.0000)
    lonlat_minmax[6][30] = (127.7013, 150.1207, 20.0000, 30.0000)
    lonlat_minmax[6][31] = (138.3431, 161.6677, 20.0000, 30.0000)
    lonlat_minmax[6][32] = (148.9849, 173.2147, 20.0000, 30.0000)
    lonlat_minmax[6][33] = (159.6267, 180.0000, 20.0000, 30.0000)
    lonlat_minmax[6][34] = (170.2684, 180.0000, 20.0000, 27.2667)
    lonlat_minmax[7][0] = (-180.0000, -172.6141, 10.0000, 19.1917)
    lonlat_minmax[7][1] = (-180.0000, -162.4598, 10.0000, 20.0000)
    lonlat_minmax[7][2] = (-170.2684, -152.3055, 10.0000, 20.0000)
    lonlat_minmax[7][3] = (-159.6267, -142.1513, 10.0000, 20.0000)
    lonlat_minmax[7][4] = (-148.9849, -131.9970, 10.0000, 20.0000)
    lonlat_minmax[7][5] = (-138.3431, -121.8427, 10.0000, 20.0000)
    lonlat_minmax[7][6] = (-127.7013, -111.6885, 10.0000, 20.0000)
    lonlat_minmax[7][7] = (-117.0596, -101.5342, 10.0000, 20.0000)
    lonlat_minmax[7][8] = (-106.4178, -91.3799, 10.0000, 20.0000)
    lonlat_minmax[7][9] = (-95.7760, -81.2257, 10.0000, 20.0000)
    lonlat_minmax[7][10] = (-85.1342, -71.0714, 10.0000, 20.0000)
    lonlat_minmax[7][11] = (-74.4924, -60.9171, 10.0000, 20.0000)
    lonlat_minmax[7][12] = (-63.8507, -50.7629, 10.0000, 20.0000)
    lonlat_minmax[7][13] = (-53.2089, -40.6086, 10.0000, 20.0000)
    lonlat_minmax[7][14] = (-42.5671, -30.4543, 10.0000, 20.0000)
    lonlat_minmax[7][15] = (-31.9253, -20.3001, 10.0000, 20.0000)
    lonlat_minmax[7][16] = (-21.2836, -10.1458, 10.0000, 20.0000)
    lonlat_minmax[7][17] = (-10.6418, 0.0089, 10.0000, 20.0000)
    lonlat_minmax[7][18] = (0.0000, 10.6506, 10.0000, 20.0000)
    lonlat_minmax[7][19] = (10.1543, 21.2924, 10.0000, 20.0000)
    lonlat_minmax[7][20] = (20.3085, 31.9342, 10.0000, 20.0000)
    lonlat_minmax[7][21] = (30.4628, 42.5760, 10.0000, 20.0000)
    lonlat_minmax[7][22] = (40.6171, 53.2178, 10.0000, 20.0000)
    lonlat_minmax[7][23] = (50.7713, 63.8595, 10.0000, 20.0000)
    lonlat_minmax[7][24] = (60.9256, 74.5013, 10.0000, 20.0000)
    lonlat_minmax[7][25] = (71.0799, 85.1431, 10.0000, 20.0000)
    lonlat_minmax[7][26] = (81.2341, 95.7849, 10.0000, 20.0000)
    lonlat_minmax[7][27] = (91.3884, 106.4266, 10.0000, 20.0000)
    lonlat_minmax[7][28] = (101.5427, 117.0684, 10.0000, 20.0000)
    lonlat_minmax[7][29] = (111.6969, 127.7102, 10.0000, 20.0000)
    lonlat_minmax[7][30] = (121.8512, 138.3520, 10.0000, 20.0000)
    lonlat_minmax[7][31] = (132.0055, 148.9938, 10.0000, 20.0000)
    lonlat_minmax[7][32] = (142.1597, 159.6355, 10.0000, 20.0000)
    lonlat_minmax[7][33] = (152.3140, 170.2773, 10.0000, 20.0000)
    lonlat_minmax[7][34] = (162.4683, 180.0000, 10.0000, 20.0000)
    lonlat_minmax[7][35] = (172.6225, 180.0000, 10.0000, 19.1833)
    lonlat_minmax[8][0] = (-180.0000, -169.9917, -0.0000, 10.0000)
    lonlat_minmax[8][1] = (-172.6225, -159.9917, -0.0000, 10.0000)
    lonlat_minmax[8][2] = (-162.4683, -149.9917, -0.0000, 10.0000)
    lonlat_minmax[8][3] = (-152.3140, -139.9917, -0.0000, 10.0000)
    lonlat_minmax[8][4] = (-142.1597, -129.9917, -0.0000, 10.0000)
    lonlat_minmax[8][5] = (-132.0055, -119.9917, -0.0000, 10.0000)
    lonlat_minmax[8][6] = (-121.8512, -109.9917, -0.0000, 10.0000)
    lonlat_minmax[8][7] = (-111.6969, -99.9917, -0.0000, 10.0000)
    lonlat_minmax[8][8] = (-101.5427, -89.9917, -0.0000, 10.0000)
    lonlat_minmax[8][9] = (-91.3884, -79.9917, -0.0000, 10.0000)
    lonlat_minmax[8][10] = (-81.2341, -69.9917, -0.0000, 10.0000)
    lonlat_minmax[8][11] = (-71.0799, -59.9917, -0.0000, 10.0000)
    lonlat_minmax[8][12] = (-60.9256, -49.9917, -0.0000, 10.0000)
    lonlat_minmax[8][13] = (-50.7713, -39.9917, -0.0000, 10.0000)
    lonlat_minmax[8][14] = (-40.6171, -29.9917, -0.0000, 10.0000)
    lonlat_minmax[8][15] = (-30.4628, -19.9917, -0.0000, 10.0000)
    lonlat_minmax[8][16] = (-20.3085, -9.9917, -0.0000, 10.0000)
    lonlat_minmax[8][17] = (-10.1543, 0.0085, -0.0000, 10.0000)
    lonlat_minmax[8][18] = (0.0000, 10.1627, -0.0000, 10.0000)
    lonlat_minmax[8][19] = (10.0000, 20.3170, -0.0000, 10.0000)
    lonlat_minmax[8][20] = (20.0000, 30.4713, -0.0000, 10.0000)
    lonlat_minmax[8][21] = (30.0000, 40.6255, -0.0000, 10.0000)
    lonlat_minmax[8][22] = (40.0000, 50.7798, -0.0000, 10.0000)
    lonlat_minmax[8][23] = (50.0000, 60.9341, -0.0000, 10.0000)
    lonlat_minmax[8][24] = (60.0000, 71.0883, -0.0000, 10.0000)
    lonlat_minmax[8][25] = (70.0000, 81.2426, -0.0000, 10.0000)
    lonlat_minmax[8][26] = (80.0000, 91.3969, -0.0000, 10.0000)
    lonlat_minmax[8][27] = (90.0000, 101.5511, -0.0000, 10.0000)
    lonlat_minmax[8][28] = (100.0000, 111.7054, -0.0000, 10.0000)
    lonlat_minmax[8][29] = (110.0000, 121.8597, -0.0000, 10.0000)
    lonlat_minmax[8][30] = (120.0000, 132.0139, -0.0000, 10.0000)
    lonlat_minmax[8][31] = (130.0000, 142.1682, -0.0000, 10.0000)
    lonlat_minmax[8][32] = (140.0000, 152.3225, -0.0000, 10.0000)
    lonlat_minmax[8][33] = (150.0000, 162.4767, -0.0000, 10.0000)
    lonlat_minmax[8][34] = (160.0000, 172.6310, -0.0000, 10.0000)
    lonlat_minmax[8][35] = (170.0000, 180.0000, -0.0000, 10.0000)
    lonlat_minmax[9][0] = (-180.0000, -169.9917, -10.0000, -0.0000)
    lonlat_minmax[9][1] = (-172.6225, -159.9917, -10.0000, -0.0000)
    lonlat_minmax[9][2] = (-162.4683, -149.9917, -10.0000, -0.0000)
    lonlat_minmax[9][3] = (-152.3140, -139.9917, -10.0000, -0.0000)
    lonlat_minmax[9][4] = (-142.1597, -129.9917, -10.0000, -0.0000)
    lonlat_minmax[9][5] = (-132.0055, -119.9917, -10.0000, -0.0000)
    lonlat_minmax[9][6] = (-121.8512, -109.9917, -10.0000, -0.0000)
    lonlat_minmax[9][7] = (-111.6969, -99.9917, -10.0000, -0.0000)
    lonlat_minmax[9][8] = (-101.5427, -89.9917, -10.0000, -0.0000)
    lonlat_minmax[9][9] = (-91.3884, -79.9917, -10.0000, -0.0000)
    lonlat_minmax[9][10] = (-81.2341, -69.9917, -10.0000, -0.0000)
    lonlat_minmax[9][11] = (-71.0799, -59.9917, -10.0000, -0.0000)
    lonlat_minmax[9][12] = (-60.9256, -49.9917, -10.0000, -0.0000)
    lonlat_minmax[9][13] = (-50.7713, -39.9917, -10.0000, -0.0000)
    lonlat_minmax[9][14] = (-40.6171, -29.9917, -10.0000, -0.0000)
    lonlat_minmax[9][15] = (-30.4628, -19.9917, -10.0000, -0.0000)
    lonlat_minmax[9][16] = (-20.3085, -9.9917, -10.0000, -0.0000)
    lonlat_minmax[9][17] = (-10.1543, 0.0085, -10.0000, -0.0000)
    lonlat_minmax[9][18] = (0.0000, 10.1627, -10.0000, -0.0000)
    lonlat_minmax[9][19] = (10.0000, 20.3170, -10.0000, -0.0000)
    lonlat_minmax[9][20] = (20.0000, 30.4713, -10.0000, -0.0000)
    lonlat_minmax[9][21] = (30.0000, 40.6255, -10.0000, -0.0000)
    lonlat_minmax[9][22] = (40.0000, 50.7798, -10.0000, -0.0000)
    lonlat_minmax[9][23] = (50.0000, 60.9341, -10.0000, -0.0000)
    lonlat_minmax[9][24] = (60.0000, 71.0883, -10.0000, -0.0000)
    lonlat_minmax[9][25] = (70.0000, 81.2426, -10.0000, -0.0000)
    lonlat_minmax[9][26] = (80.0000, 91.3969, -10.0000, -0.0000)
    lonlat_minmax[9][27] = (90.0000, 101.5511, -10.0000, -0.0000)
    lonlat_minmax[9][28] = (100.0000, 111.7054, -10.0000, -0.0000)
    lonlat_minmax[9][29] = (110.0000, 121.8597, -10.0000, -0.0000)
    lonlat_minmax[9][30] = (120.0000, 132.0139, -10.0000, -0.0000)
    lonlat_minmax[9][31] = (130.0000, 142.1682, -10.0000, -0.0000)
    lonlat_minmax[9][32] = (140.0000, 152.3225, -10.0000, -0.0000)
    lonlat_minmax[9][33] = (150.0000, 162.4767, -10.0000, -0.0000)
    lonlat_minmax[9][34] = (160.0000, 172.6310, -10.0000, -0.0000)
    lonlat_minmax[9][35] = (170.0000, 180.0000, -10.0000, -0.0000)
    lonlat_minmax[10][0] = (-180.0000, -172.6141, -19.1917, -10.0000)
    lonlat_minmax[10][1] = (-180.0000, -162.4598, -20.0000, -10.0000)
    lonlat_minmax[10][2] = (-170.2684, -152.3055, -20.0000, -10.0000)
    lonlat_minmax[10][3] = (-159.6267, -142.1513, -20.0000, -10.0000)
    lonlat_minmax[10][4] = (-148.9849, -131.9970, -20.0000, -10.0000)
    lonlat_minmax[10][5] = (-138.3431, -121.8427, -20.0000, -10.0000)
    lonlat_minmax[10][6] = (-127.7013, -111.6885, -20.0000, -10.0000)
    lonlat_minmax[10][7] = (-117.0596, -101.5342, -20.0000, -10.0000)
    lonlat_minmax[10][8] = (-106.4178, -91.3799, -20.0000, -10.0000)
    lonlat_minmax[10][9] = (-95.7760, -81.2257, -20.0000, -10.0000)
    lonlat_minmax[10][10] = (-85.1342, -71.0714, -20.0000, -10.0000)
    lonlat_minmax[10][11] = (-74.4924, -60.9171, -20.0000, -10.0000)
    lonlat_minmax[10][12] = (-63.8507, -50.7629, -20.0000, -10.0000)
    lonlat_minmax[10][13] = (-53.2089, -40.6086, -20.0000, -10.0000)
    lonlat_minmax[10][14] = (-42.5671, -30.4543, -20.0000, -10.0000)
    lonlat_minmax[10][15] = (-31.9253, -20.3001, -20.0000, -10.0000)
    lonlat_minmax[10][16] = (-21.2836, -10.1458, -20.0000, -10.0000)
    lonlat_minmax[10][17] = (-10.6418, 0.0089, -20.0000, -10.0000)
    lonlat_minmax[10][18] = (0.0000, 10.6506, -20.0000, -10.0000)
    lonlat_minmax[10][19] = (10.1543, 21.2924, -20.0000, -10.0000)
    lonlat_minmax[10][20] = (20.3085, 31.9342, -20.0000, -10.0000)
    lonlat_minmax[10][21] = (30.4628, 42.5760, -20.0000, -10.0000)
    lonlat_minmax[10][22] = (40.6171, 53.2178, -20.0000, -10.0000)
    lonlat_minmax[10][23] = (50.7713, 63.8595, -20.0000, -10.0000)
    lonlat_minmax[10][24] = (60.9256, 74.5013, -20.0000, -10.0000)
    lonlat_minmax[10][25] = (71.0799, 85.1431, -20.0000, -10.0000)
    lonlat_minmax[10][26] = (81.2341, 95.7849, -20.0000, -10.0000)
    lonlat_minmax[10][27] = (91.3884, 106.4266, -20.0000, -10.0000)
    lonlat_minmax[10][28] = (101.5427, 117.0684, -20.0000, -10.0000)
    lonlat_minmax[10][29] = (111.6969, 127.7102, -20.0000, -10.0000)
    lonlat_minmax[10][30] = (121.8512, 138.3520, -20.0000, -10.0000)
    lonlat_minmax[10][31] = (132.0055, 148.9938, -20.0000, -10.0000)
    lonlat_minmax[10][32] = (142.1597, 159.6355, -20.0000, -10.0000)
    lonlat_minmax[10][33] = (152.3140, 170.2773, -20.0000, -10.0000)
    lonlat_minmax[10][34] = (162.4683, 180.0000, -20.0000, -10.0000)
    lonlat_minmax[10][35] = (172.6225, 180.0000, -19.1833, -10.0000)
    lonlat_minmax[11][1] = (-180.0000, -170.2596, -27.2667, -20.0000)
    lonlat_minmax[11][2] = (-180.0000, -159.6178, -30.0000, -20.0000)
    lonlat_minmax[11][3] = (-173.2051, -148.9760, -30.0000, -20.0000)
    lonlat_minmax[11][4] = (-161.6581, -138.3342, -30.0000, -20.0000)
    lonlat_minmax[11][5] = (-150.1111, -127.6925, -30.0000, -20.0000)
    lonlat_minmax[11][6] = (-138.5641, -117.0507, -30.0000, -20.0000)
    lonlat_minmax[11][7] = (-127.0171, -106.4089, -30.0000, -20.0000)
    lonlat_minmax[11][8] = (-115.4701, -95.7671, -30.0000, -20.0000)
    lonlat_minmax[11][9] = (-103.9230, -85.1254, -30.0000, -20.0000)
    lonlat_minmax[11][10] = (-92.3760, -74.4836, -30.0000, -20.0000)
    lonlat_minmax[11][11] = (-80.8290, -63.8418, -30.0000, -20.0000)
    lonlat_minmax[11][12] = (-69.2820, -53.2000, -30.0000, -20.0000)
    lonlat_minmax[11][13] = (-57.7350, -42.5582, -30.0000, -20.0000)
    lonlat_minmax[11][14] = (-46.1880, -31.9165, -30.0000, -20.0000)
    lonlat_minmax[11][15] = (-34.6410, -21.2747, -30.0000, -20.0000)
    lonlat_minmax[11][16] = (-23.0940, -10.6329, -30.0000, -20.0000)
    lonlat_minmax[11][17] = (-11.5470, 0.0096, -30.0000, -20.0000)
    lonlat_minmax[11][18] = (0.0000, 11.5566, -30.0000, -20.0000)
    lonlat_minmax[11][19] = (10.6418, 23.1036, -30.0000, -20.0000)
    lonlat_minmax[11][20] = (21.2836, 34.6506, -30.0000, -20.0000)
    lonlat_minmax[11][21] = (31.9253, 46.1976, -30.0000, -20.0000)
    lonlat_minmax[11][22] = (42.5671, 57.7446, -30.0000, -20.0000)
    lonlat_minmax[11][23] = (53.2089, 69.2917, -30.0000, -20.0000)
    lonlat_minmax[11][24] = (63.8507, 80.8387, -30.0000, -20.0000)
    lonlat_minmax[11][25] = (74.4924, 92.3857, -30.0000, -20.0000)
    lonlat_minmax[11][26] = (85.1342, 103.9327, -30.0000, -20.0000)
    lonlat_minmax[11][27] = (95.7760, 115.4797, -30.0000, -20.0000)
    lonlat_minmax[11][28] = (106.4178, 127.0267, -30.0000, -20.0000)
    lonlat_minmax[11][29] = (117.0596, 138.5737, -30.0000, -20.0000)
    lonlat_minmax[11][30] = (127.7013, 150.1207, -30.0000, -20.0000)
    lonlat_minmax[11][31] = (138.3431, 161.6677, -30.0000, -20.0000)
    lonlat_minmax[11][32] = (148.9849, 173.2147, -30.0000, -20.0000)
    lonlat_minmax[11][33] = (159.6267, 180.0000, -30.0000, -20.0000)
    lonlat_minmax[11][34] = (170.2684, 180.0000, -27.2667, -20.0000)
    lonlat_minmax[12][2] = (-180.0000, -173.1955, -33.5583, -30.0000)
    lonlat_minmax[12][3] = (-180.0000, -161.6485, -38.9500, -30.0000)
    lonlat_minmax[12][4] = (-180.0000, -150.1014, -40.0000, -30.0000)
    lonlat_minmax[12][5] = (-169.7029, -138.5544, -40.0000, -30.0000)
    lonlat_minmax[12][6] = (-156.6489, -127.0074, -40.0000, -30.0000)
    lonlat_minmax[12][7] = (-143.5948, -115.4604, -40.0000, -30.0000)
    lonlat_minmax[12][8] = (-130.5407, -103.9134, -40.0000, -30.0000)
    lonlat_minmax[12][9] = (-117.4867, -92.3664, -40.0000, -30.0000)
    lonlat_minmax[12][10] = (-104.4326, -80.8194, -40.0000, -30.0000)
    lonlat_minmax[12][11] = (-91.3785, -69.2724, -40.0000, -30.0000)
    lonlat_minmax[12][12] = (-78.3244, -57.7254, -40.0000, -30.0000)
    lonlat_minmax[12][13] = (-65.2704, -46.1784, -40.0000, -30.0000)
    lonlat_minmax[12][14] = (-52.2163, -34.6314, -40.0000, -30.0000)
    lonlat_minmax[12][15] = (-39.1622, -23.0844, -40.0000, -30.0000)
    lonlat_minmax[12][16] = (-26.1081, -11.5374, -40.0000, -30.0000)
    lonlat_minmax[12][17] = (-13.0541, 0.0109, -40.0000, -30.0000)
    lonlat_minmax[12][18] = (0.0000, 13.0650, -40.0000, -30.0000)
    lonlat_minmax[12][19] = (11.5470, 26.1190, -40.0000, -30.0000)
    lonlat_minmax[12][20] = (23.0940, 39.1731, -40.0000, -30.0000)
    lonlat_minmax[12][21] = (34.6410, 52.2272, -40.0000, -30.0000)
    lonlat_minmax[12][22] = (46.1880, 65.2812, -40.0000, -30.0000)
    lonlat_minmax[12][23] = (57.7350, 78.3353, -40.0000, -30.0000)
    lonlat_minmax[12][24] = (69.2820, 91.3894, -40.0000, -30.0000)
    lonlat_minmax[12][25] = (80.8290, 104.4435, -40.0000, -30.0000)
    lonlat_minmax[12][26] = (92.3760, 117.4975, -40.0000, -30.0000)
    lonlat_minmax[12][27] = (103.9230, 130.5516, -40.0000, -30.0000)
    lonlat_minmax[12][28] = (115.4701, 143.6057, -40.0000, -30.0000)
    lonlat_minmax[12][29] = (127.0171, 156.6598, -40.0000, -30.0000)
    lonlat_minmax[12][30] = (138.5641, 169.7138, -40.0000, -30.0000)
    lonlat_minmax[12][31] = (150.1111, 180.0000, -40.0000, -30.0000)
    lonlat_minmax[12][32] = (161.6581, 180.0000, -38.9417, -30.0000)
    lonlat_minmax[12][33] = (173.2051, 180.0000, -33.5583, -30.0000)
    lonlat_minmax[13][4] = (-180.0000, -169.6921, -43.7667, -40.0000)
    lonlat_minmax[13][5] = (-180.0000, -156.6380, -48.1917, -40.0000)
    lonlat_minmax[13][6] = (-180.0000, -143.5839, -50.0000, -40.0000)
    lonlat_minmax[13][7] = (-171.1296, -130.5299, -50.0000, -40.0000)
    lonlat_minmax[13][8] = (-155.5724, -117.4758, -50.0000, -40.0000)
    lonlat_minmax[13][9] = (-140.0151, -104.4217, -50.0000, -40.0000)
    lonlat_minmax[13][10] = (-124.4579, -91.3676, -50.0000, -40.0000)
    lonlat_minmax[13][11] = (-108.9007, -78.3136, -50.0000, -40.0000)
    lonlat_minmax[13][12] = (-93.3434, -65.2595, -50.0000, -40.0000)
    lonlat_minmax[13][13] = (-77.7862, -52.2054, -50.0000, -40.0000)
    lonlat_minmax[13][14] = (-62.2290, -39.1513, -50.0000, -40.0000)
    lonlat_minmax[13][15] = (-46.6717, -26.0973, -50.0000, -40.0000)
    lonlat_minmax[13][16] = (-31.1145, -13.0432, -50.0000, -40.0000)
    lonlat_minmax[13][17] = (-15.5572, 0.0130, -50.0000, -40.0000)
    lonlat_minmax[13][18] = (0.0000, 15.5702, -50.0000, -40.0000)
    lonlat_minmax[13][19] = (13.0541, 31.1274, -50.0000, -40.0000)
    lonlat_minmax[13][20] = (26.1081, 46.6847, -50.0000, -40.0000)
    lonlat_minmax[13][21] = (39.1622, 62.2419, -50.0000, -40.0000)
    lonlat_minmax[13][22] = (52.2163, 77.7992, -50.0000, -40.0000)
    lonlat_minmax[13][23] = (65.2704, 93.3564, -50.0000, -40.0000)
    lonlat_minmax[13][24] = (78.3244, 108.9136, -50.0000, -40.0000)
    lonlat_minmax[13][25] = (91.3785, 124.4709, -50.0000, -40.0000)
    lonlat_minmax[13][26] = (104.4326, 140.0281, -50.0000, -40.0000)
    lonlat_minmax[13][27] = (117.4867, 155.5853, -50.0000, -40.0000)
    lonlat_minmax[13][28] = (130.5407, 171.1426, -50.0000, -40.0000)
    lonlat_minmax[13][29] = (143.5948, 180.0000, -50.0000, -40.0000)
    lonlat_minmax[13][30] = (156.6489, 180.0000, -48.1917, -40.0000)
    lonlat_minmax[13][31] = (169.7029, 180.0000, -43.7583, -40.0000)
    lonlat_minmax[14][6] = (-180.0000, -171.1167, -52.3333, -50.0000)
    lonlat_minmax[14][7] = (-180.0000, -155.5594, -56.2583, -50.0000)
    lonlat_minmax[14][8] = (-180.0000, -140.0022, -60.0000, -50.0000)
    lonlat_minmax[14][9] = (-180.0000, -124.4449, -60.0000, -50.0000)
    lonlat_minmax[14][10] = (-160.0000, -108.8877, -60.0000, -50.0000)
    lonlat_minmax[14][11] = (-140.0000, -93.3305, -60.0000, -50.0000)
    lonlat_minmax[14][12] = (-120.0000, -77.7732, -60.0000, -50.0000)
    lonlat_minmax[14][13] = (-100.0000, -62.2160, -60.0000, -50.0000)
    lonlat_minmax[14][14] = (-80.0000, -46.6588, -60.0000, -50.0000)
    lonlat_minmax[14][15] = (-60.0000, -31.1015, -60.0000, -50.0000)
    lonlat_minmax[14][16] = (-40.0000, -15.5443, -60.0000, -50.0000)
    lonlat_minmax[14][17] = (-20.0000, 0.0167, -60.0000, -50.0000)
    lonlat_minmax[14][18] = (0.0000, 20.0167, -60.0000, -50.0000)
    lonlat_minmax[14][19] = (15.5572, 40.0167, -60.0000, -50.0000)
    lonlat_minmax[14][20] = (31.1145, 60.0167, -60.0000, -50.0000)
    lonlat_minmax[14][21] = (46.6717, 80.0167, -60.0000, -50.0000)
    lonlat_minmax[14][22] = (62.2290, 100.0167, -60.0000, -50.0000)
    lonlat_minmax[14][23] = (77.7862, 120.0167, -60.0000, -50.0000)
    lonlat_minmax[14][24] = (93.3434, 140.0167, -60.0000, -50.0000)
    lonlat_minmax[14][25] = (108.9007, 160.0167, -60.0000, -50.0000)
    lonlat_minmax[14][26] = (124.4579, 180.0000, -60.0000, -50.0000)
    lonlat_minmax[14][27] = (140.0151, 180.0000, -60.0000, -50.0000)
    lonlat_minmax[14][28] = (155.5724, 180.0000, -56.2500, -50.0000)
    lonlat_minmax[14][29] = (171.1296, 180.0000, -52.3333, -50.0000)
    lonlat_minmax[15][9] = (-180.0000, -159.9833, -63.6167, -60.0000)
    lonlat_minmax[15][10] = (-180.0000, -139.9833, -67.1167, -60.0000)
    lonlat_minmax[15][11] = (-180.0000, -119.9833, -70.0000, -60.0000)
    lonlat_minmax[15][12] = (-175.4283, -99.9833, -70.0000, -60.0000)
    lonlat_minmax[15][13] = (-146.1902, -79.9833, -70.0000, -60.0000)
    lonlat_minmax[15][14] = (-116.9522, -59.9833, -70.0000, -60.0000)
    lonlat_minmax[15][15] = (-87.7141, -39.9833, -70.0000, -60.0000)
    lonlat_minmax[15][16] = (-58.4761, -19.9833, -70.0000, -60.0000)
    lonlat_minmax[15][17] = (-29.2380, 0.0244, -70.0000, -60.0000)
    lonlat_minmax[15][18] = (0.0000, 29.2624, -70.0000, -60.0000)
    lonlat_minmax[15][19] = (20.0000, 58.5005, -70.0000, -60.0000)
    lonlat_minmax[15][20] = (40.0000, 87.7385, -70.0000, -60.0000)
    lonlat_minmax[15][21] = (60.0000, 116.9765, -70.0000, -60.0000)
    lonlat_minmax[15][22] = (80.0000, 146.2146, -70.0000, -60.0000)
    lonlat_minmax[15][23] = (100.0000, 175.4526, -70.0000, -60.0000)
    lonlat_minmax[15][24] = (120.0000, 180.0000, -70.0000, -60.0000)
    lonlat_minmax[15][25] = (140.0000, 180.0000, -67.1167, -60.0000)
    lonlat_minmax[15][26] = (160.0000, 180.0000, -63.6167, -60.0000)
    lonlat_minmax[16][11] = (-180.0000, -175.4039, -70.5333, -70.0000)
    lonlat_minmax[16][12] = (-180.0000, -146.1659, -73.8750, -70.0000)
    lonlat_minmax[16][13] = (-180.0000, -116.9278, -77.1667, -70.0000)
    lonlat_minmax[16][14] = (-180.0000, -87.6898, -80.0000, -70.0000)
    lonlat_minmax[16][15] = (-172.7631, -58.4517, -80.0000, -70.0000)
    lonlat_minmax[16][16] = (-115.1754, -29.2137, -80.0000, -70.0000)
    lonlat_minmax[16][17] = (-57.5877, 0.0480, -80.0000, -70.0000)
    lonlat_minmax[16][18] = (0.0000, 57.6357, -80.0000, -70.0000)
    lonlat_minmax[16][19] = (29.2380, 115.2234, -80.0000, -70.0000)
    lonlat_minmax[16][20] = (58.4761, 172.8111, -80.0000, -70.0000)
    lonlat_minmax[16][21] = (87.7141, 180.0000, -80.0000, -70.0000)
    lonlat_minmax[16][22] = (116.9522, 180.0000, -77.1583, -70.0000)
    lonlat_minmax[16][23] = (146.1902, 180.0000, -73.8750, -70.0000)
    lonlat_minmax[16][24] = (175.4283, 180.0000, -70.5333, -70.0000)
    lonlat_minmax[17][14] = (-180.0000, -172.7151, -80.4083, -80.0000)
    lonlat_minmax[17][15] = (-180.0000, -115.1274, -83.6250, -80.0000)
    lonlat_minmax[17][16] = (-180.0000, -57.5397, -86.8167, -80.0000)
    lonlat_minmax[17][17] = (-180.0000, 57.2957, -90.0000, -80.0000)
    lonlat_minmax[17][18] = (-0.0040, 180.0000, -90.0000, -80.0000)
    lonlat_minmax[17][19] = (57.5877, 180.0000, -86.8167, -80.0000)
    lonlat_minmax[17][20] = (115.1754, 180.0000, -83.6250, -80.0000)
    lonlat_minmax[17][21] = (172.7631, 180.0000, -80.4083, -80.0000)

    try:
        is_valid_tileID = True
        lon_min, lon_max, lat_min, lat_max = lonlat_minmax[vID][hID]

        # Don't use negative 0.0  Correct this by adding 0 to the variable
        # (I'm not sure why such values are tabulated in the original file?)
        lon_min += 0
        lon_max += 0
        lat_min += 0
        lat_max += 0
    except KeyError:
        is_valid_tileID = False
        lon_min, lon_max, lat_min, lat_max = -999.0, -999.0, -99.0, -99.0

    return is_valid_tileID, lon_min, lon_max, lat_min, lat_max


if __name__ == "__main__":
    tile_label = sys.argv[1]
    hID, vID = get_tiletuple_from_arg(tile_label)

    is_valid_tileID, lon_min, lon_max, lat_min, lat_max = look_up_latlon_minmax(
        hID, vID
    )

    if not is_valid_tileID:
        print(f"{tile_label} is not a valid MODIS land tile")
        exit(0)

    xmin, xmax, ymin, ymax = get_xy_minmax(hID, vID)
    geotransform_string = get_geotransform(hID, vID)

    # For bounds in projected x- and y-
    # geospatial_bounds_str = get_geospatial_bounds_xy(hID, vID)

    # For bounds in latitude and longitude (ie EPSG:4326)
    geospatial_bounds_str = get_geospatial_bounds_latlon(hID, vID)

    print()
    print(f"tile indices of: {tile_label}")
    print(f"  horizontal index: {hID:02d}")
    print(f"    vertical index: {vID:02d}")
    print()
    print("  Projected extents:")
    print(f"     xmin: {xmin:15.5f}    xmax: {xmax:15.5f}")
    print(f"     ymin: {ymin:15.5f}    ymax: {ymax:15.5f}")
    print()
    print(f"  geospatial_lon_min: {lon_min}")
    print(f"  geospatial_lon_max: {lon_max}")
    print()
    print(f"  geospatial_lat_min: {lat_min}")
    print(f"  geospatial_lat_max: {lat_max}")
    print()
    print("  geotransform_string:")
    print(f"     {geotransform_string}")
    print()
    print("  geospatial_bounds_str:")
    print(f"     {geospatial_bounds_str}")
    print()
