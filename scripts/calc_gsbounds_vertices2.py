"""Calculate the geospatial_bounds vertices for
MODIS sinu tiles, where

Usage:
    python calc_gsbounds_vertices2.py

yields:
    Ran all the polygons; number of valid tiles: 460
    Wrote: modis_tile_lonlat_bounds.txt
    Wrote: modis_tile_geospatial_bounds.yml

After running this file, run:
    python create_allpoly_shpfile.py
which will create shapefiles for each of the valid modsinu grid tiles:
       modsinu_latlon_bounds_{tileID}.shp.zip'
    eg:
       modsinu_latlon_bounds_h09v05.shp.zip'
    which are moved after being created to the local directory:
       ./modsinu_latlon_bounds_files/

and then will  combine all of these into a single shapefile:
    MODIS_tile_boundaries.shp
"""

import numpy as np
from osgeo import gdal, osr
import yaml
from pprint import pprint as pp

# This avoids a FutureWarning for GDAL 4.0
osr.UseExceptions()

# This is the pixel size for the "500m" "MODIS" sinusoidal grid [=modsinu]
# This value is mathematically calculated so that 2400 * 18 * ps yields
#   the same value as:
#     $ echo "-180.0 0.0" | gdaltransform -i -s_srs '+proj=sinu +R=6371007.181' -t_srs EPSG:4326
#     -20015109.3557974 0 0
ps = 463.31271656938424

# For reference, these are the edge distances in meters for modsinu
# xleft = -20015109.3557974
# ytop = 10007554.6778987

vert_dict = {}
horiz_dict = {}

def get_sn2ll():
    """Returns the coordinate transformation object
    for MODISsinusoidalgrid-to-WGS84LatLon"""
    srs_ll = osr.SpatialReference()
    srs_ll.ImportFromEPSG(4326)

    srs_sn = osr.SpatialReference()
    srs_sn.ImportFromProj4('proj=sinu +R=6371007.18042786')

    sn2ll = osr.CoordinateTransformation(srs_sn, srs_ll)

    return sn2ll


def compute_horizontal_bounds_UR():
    """ Compute horiz_bounds for the Upper Right modsinu quadrant
        h18v00 - h36v09

    These are the bounds across lines of latitude in the sinusoidal grid.

    We loop upward from the equator in 10-degree increments,
      and fill the horiz_bounds_[lon/lat] fields as we move away from Greenwich
    Note:
      h00 is i-index 0     v00 is j-index 00
      h36 is i-index 36    v18 is j-index 18

    Note: horiz needs to go all the way to edge because 10deg in from -180/180 on modsinu
          is not quite to -180/180 on epsg4236_latlon
    """
    sn2ll = get_sn2ll()

    # Note: horiz_bounds_lat/lon are defined for the full grid
    #       even though this first routine only computes the upper-right quadrant values
    horiz_bounds_lon = np.full((37, 19), np.nan, dtype=np.float64)
    horiz_bounds_lat = np.full((37, 19), np.nan, dtype=np.float64)
    horiz_extend_lon = np.full((37, 19), np.nan, dtype=np.float64)
    horiz_extend_lat = np.full((37, 19), np.nan, dtype=np.float64)

    # This is the last pixel west of Greenwich at 1-deg increments in y
    # that does not (mathematically) cross the -180/180o line
    # Note: for eastern longitudes, this will mean a switch from positive (toward 180) longitudes to negative
    # Note: 0 is max North at North Pole
    #       Northern latitudes are indices 0-8
    #       9 is exactly 0 deg latitude

    # Note: 240 pixels per sn_degree

    # Set manually for North Pole
    horiz_bounds_lat[18, 0] = 90.0
    horiz_bounds_lon[18, 0] = 0.0  # Here, longitude is degenerate

    # Set manually for South Pole
    horiz_bounds_lat[18, 18] = -90.0
    horiz_bounds_lon[18, 18] = 0.0  # Here, longitude is degenerate

    # Set manually for "East Pole"
    horiz_bounds_lat[36, 9] = 0.0
    horiz_bounds_lon[36, 9] = 180.0

    # Set manually for "West Pole"
    horiz_bounds_lat[0, 9] = 0.0
    # horiz_bounds_lon[0, 9] = -179.9999
    horiz_bounds_lon[0, 9] = -180.0

    # Loop for other latitudes:
    for sn_lat in range(0, 90, 10):
        sn_y = sn_lat * 240 * ps
        v_idx = (90 - sn_lat) // 10
        print()
        print(f'Computing for sn_lat: {sn_lat} (v_idx: {v_idx:02d}),  sn_y: {sn_y}')

        # March eastward in longitude at this latitude
        #  If we cross from positive longitude to negative, we have crossed the 180o line and need to backtrack
        # We attempt 10-degree
        crossed_180o = False
        for sn_lon in range(0, 180+1, 10):
            sn_x = sn_lon * 240 * ps
            h_idx = (sn_lon - -180) // 10

            lat, lon, _ = sn2ll.TransformPoint(sn_x, sn_y)

            if lon < 0 or lon > 180.0 or ((sn_lat == 10) and (sn_lon  == 180)):
                # Note: This fails to find a value for (36, 9),
                #       so that must be set a priori to lat=0, lon=180
                print(f'lon crossed 180o moving horiz for {h_idx} {v_idx}')
                # We have crossed 180o.
                crossed_180o = True

                # Back off and step in one-sn_pixel increments
                sn_lon -= 10

                # So...at 60 deg N, this goes oob *exactly* at the boundary
                #   so add 1 to the search range to catch that
                # for sn_i in range(sn_lon * 240, (sn_lon + 10) * 240):
                for sn_i in range(sn_lon * 240, (sn_lon + 10) * 240 + 2):
                    sn_x = sn_i * ps
                    lat, lon, _ = sn2ll.TransformPoint(sn_x, sn_y)

                    # if sn_lat == 60:
                    #     # Debug the v03 loop...
                    #     print(f' h{h_idx}v{v_idx}: sn_x: {sn_x} lon: {lon} (sn_i: {sn_i} / {(sn_lon + 10) * 240})')
                    #     # if sn_i == 21599:
                    #     #     print('debug...')
                    #     #     breakpoint()

                    if lon < 0:
                        # We have crossed 180o.  Back off to get last-valid sn_i
                        sn_i -= 1
                        sn_x = sn_i * ps
                        lat, lon, _ = sn2ll.TransformPoint(sn_x, sn_y)
                        # Use this lat, and use 180 as lon
                        # print(f'Setting horiz_extend for : {h_idx}, {v_idx}  {lon:.5f}=>180.0 {lat:.5f}')
                        lon = 180.000
                        horiz_extend_lat[h_idx, v_idx] = lat
                        horiz_extend_lon[h_idx, v_idx] = lon

                        break  # Break the "for sn_i..." loop
            else:
                # print(f'Setting horiz_bounds for : {h_idx}, {v_idx}  {lon:.5f} {lat:.5f}')
                horiz_bounds_lat[h_idx, v_idx] = lat
                horiz_bounds_lon[h_idx, v_idx] = lon

            if crossed_180o:
                break  # Break the "for sn_lon..." loop

    print()
    print('=================================')
    print('Finished computing UR quadrant...')
    print('=================================')
    print()

    horiz_dict['horiz_bounds_lat'] = horiz_bounds_lat
    horiz_dict['horiz_bounds_lon'] = horiz_bounds_lon
    horiz_dict['horiz_extend_lat'] = horiz_extend_lat
    horiz_dict['horiz_extend_lon'] = horiz_extend_lon
    return horiz_dict


def fill_nonUR_quadrants_horiz(horiz_dict):
    """Because the modsinu grid is symmtric, we can mirror the UR values
    across the y-axis to get the UL values.  Then, we can mirror the UL-UR
    values across the x-axis to get the LL-LR values.

    Note: horiz_bounds_lat and horiz_bounds_lon were defined
          for the entire range of values, but only the upper right
          quadrant was calculated initially.
    """
    horiz_bounds_lat = horiz_dict['horiz_bounds_lat']
    horiz_bounds_lon = horiz_dict['horiz_bounds_lon']
    horiz_extend_lat = horiz_dict['horiz_extend_lat']
    horiz_extend_lon = horiz_dict['horiz_extend_lon']

    # Flip on y-axis to fill h00-h17 v00-v08
    # Loop along each 10-degree step in x
    for hidx_ur in range(19, 36+1):
        # Mirror on y-axis, so 19->17, 20->16, etc
        hidx_ul = 36 - hidx_ur

        for vidx_ur in range(0,  9+1):
            vidx_ul = vidx_ur
            horiz_bounds_lat[hidx_ul, vidx_ul] = horiz_bounds_lat[hidx_ur, vidx_ur]
            horiz_bounds_lon[hidx_ul, vidx_ul] = -horiz_bounds_lon[hidx_ur, vidx_ur]
            horiz_extend_lat[hidx_ul, vidx_ul] = horiz_extend_lat[hidx_ur, vidx_ur]
            horiz_extend_lon[hidx_ul, vidx_ul] = -horiz_extend_lon[hidx_ur, vidx_ur]

    for hidx_u in range(0, 36+1):
        hidx_l = hidx_u

        for vidx_u in range(0,  9):
            vidx_l = 18 - vidx_u

            horiz_bounds_lat[hidx_l, vidx_l] = -horiz_bounds_lat[hidx_u, vidx_u]
            horiz_bounds_lon[hidx_l, vidx_l] = horiz_bounds_lon[hidx_u, vidx_u]
            horiz_extend_lat[hidx_l, vidx_l] = -horiz_extend_lat[hidx_u, vidx_u]
            horiz_extend_lon[hidx_l, vidx_l] = horiz_extend_lon[hidx_u, vidx_u]

    horiz_dict['horiz_bounds_lat'] = horiz_bounds_lat
    horiz_dict['horiz_bounds_lon'] = horiz_bounds_lon
    horiz_dict['horiz_extend_lat'] = horiz_extend_lat
    horiz_dict['horiz_extend_lon'] = horiz_extend_lon
    return horiz_dict


def print_horiz_bounds_UR(horiz_dict):
    """Print the Upper Right [UR] quadrant horiz_bounds_lat
    and horiz_bounds_lon arrays for visual examination"""
    horiz_bounds_lat = horiz_dict['horiz_bounds_lat']
    horiz_bounds_lon = horiz_dict['horiz_bounds_lon']
    horiz_extend_lat = horiz_dict['horiz_extend_lat']
    horiz_extend_lon = horiz_dict['horiz_extend_lon']
    print('===================================')
    print('Only the upper-right quadrant...')
    print('Latitudes:')

    # Print the header
    print('                       ', end='')  # Spacer
    for i in range(18, 36+1):
        hidx = (horiz_bounds_lon[i, 9] - -180) / 10
        print(f' h{hidx:4.1f} ', end='')
    print()

    for j in range(9 + 1):
        vidx = (90 - np.round(horiz_bounds_lat[18, j], decimals=1)) // 10
        vlat = np.round(horiz_bounds_lat[18, j], decimals=1)
        print(f'j={j:2d} vlat:{vlat:4.1f} v{vidx:4.1f}:  ', end='')
        for i in range(18, 36+1):
            if not np.isnan(horiz_bounds_lat[i, j]):
                print(f'{horiz_bounds_lat[i, j]:6.2f} ', end='')
            elif not np.isnan(horiz_extend_lat[i, j]):
                print(f'{horiz_extend_lat[i, j]:6.2f} ', end='')
            else:
                print(f'{horiz_bounds_lat[i, j]:6.2f} ', end='')
        print()

    print()
    print('Longitudes:')
    for j in range(9 + 1):
        vidx = (90 - np.round(horiz_bounds_lat[18, j], decimals=1)) // 10
        vlat = np.round(horiz_bounds_lat[18, j], decimals=1)
        print(f'j={j:2d} vlat:{vlat:4.1f} v{vidx:4.1f}:  ', end='')
        for i in range(18, 36+1):
            if not np.isnan(horiz_bounds_lon[i, j]):
                print(f'{horiz_bounds_lon[i, j]:6.2f} ', end='')
            elif not np.isnan(horiz_extend_lon[i, j]):
                print(f'{horiz_extend_lon[i, j]:6.2f} ', end='')
            else:
                print(f'{horiz_bounds_lon[i, j]:6.2f} ', end='')
        print()

    print()
    print()


def print_horiz_bounds(horiz_dict):
    """Print the horiz_bounds_lat and horiz_bounds_lon arrays for visual examination"""
    horiz_bounds_lat = horiz_dict['horiz_bounds_lat']
    horiz_bounds_lon = horiz_dict['horiz_bounds_lon']
    horiz_extend_lat = horiz_dict['horiz_extend_lat']
    horiz_extend_lon = horiz_dict['horiz_extend_lon']
    print('===================================')

    print('*** horiz_bounds ***')
    print('Note:')
    print('  leftmost in row should be -180')
    print('  rightmost in row should be 180')

    print()
    print()
    print('Full latitudes')
    # Print the header
    print('                       ', end='')  # Spacer
    for i in range(0, 36+1):
        hidx = np.round((horiz_bounds_lon[i, 9] - -180) / 10, decimals=0)
        print(f' h{hidx:02.0f}', end='')
    print()

    for j in range(18 + 1):
        vidx = (90 - np.round(horiz_bounds_lat[18, j], decimals=1)) // 10
        vlat = np.round(horiz_bounds_lat[18, j], decimals=1)
        print(f'j={j:2d} vlat:{vlat:5.1f} v{vidx:4.1f}:  ', end='')
        for i in range(0, 36+1):
            if not np.isnan(horiz_bounds_lat[i, j]):
                print(f'{horiz_bounds_lat[i, j]:3.0f} ', end='')
            elif not np.isnan(horiz_extend_lat[i, j]):
                print(f'{horiz_extend_lat[i, j]:3.0f} ', end='')
            else:
                print(f'{horiz_bounds_lat[i, j]:3.0f} ', end='')
        print()

    print('Full longitudes')
    for j in range(18 + 1):
        vidx = (90 - np.round(horiz_bounds_lat[18, j], decimals=1)) // 10
        vlat = np.round(horiz_bounds_lat[18, j], decimals=1)
        print(f'j={j:2d} vlat:{vlat:5.1f} v{vidx:4.1f}: ', end='')
        for i in range(0, 36+1):
            if not np.isnan(horiz_bounds_lat[i, j]):
                print(f'{horiz_bounds_lon[i, j]:4.0f}', end='')
            elif not np.isnan(horiz_extend_lat[i, j]):
                print(f'{horiz_extend_lon[i, j]:4.0f}', end='')
            else:
                print(f'{horiz_bounds_lon[i, j]:4.0f}', end='')
        print()


def compute_vert_bounds_UR():
    """ Compute vert_bounds
    These are the bounds across vertical lines in the sinusoidal grid

    We loop upward from the equator in 1-degree increments,
      and fill the vert_bounds_[lon/lat] fields as we move away from the equator

    Note:
     h00 is i-index 0     v000 is j-index 00.0
     h36 is i-index 36    v180 is j-index 18.0

    Note: indexing is h, v  (so: horiz, vertical)

    Note: the entire array is allocated, even though only the UR quadrant
          is calculated.
    """
    sn2ll = get_sn2ll()

    # ======================================================================
    print()
    print('Now, work on the one-degree vertical bounding vertices...')
    print()

    vert_bounds_lon = np.full((37, 181), np.nan, dtype=np.float64)
    vert_bounds_lat = np.full((37, 181), np.nan, dtype=np.float64)
    vert_extend_lon = np.full((37, 182), np.nan, dtype=np.float64)  # allow one past max j
    vert_extend_lat = np.full((37, 182), np.nan, dtype=np.float64)  # allow one past max j

    # Manually set for North Pole:
    vert_bounds_lat[18, 0] = 90.0
    vert_bounds_lon[18, 0] = 0.0  # Here, longitude is degenerate

    # Set manually for South Pole
    vert_bounds_lat[18, 180] = -90.0
    vert_bounds_lon[18, 180] = 0.0  # Here, longitude is degenerate

    # Set manually for "East Pole"
    vert_bounds_lat[36, 90] = 0.0
    vert_bounds_lon[36, 90] = 180.0

    # Set manually for "West Pole"
    vert_bounds_lat[0, 90] = 0.0
    #vert_bounds_lon[0, 90] = -179.9999
    vert_bounds_lon[0, 90] = -180.0

    # Loop in longitude by 10-degree steps
    # for sn_lon in range(0, 180, 10):
    # for sn_lon in range(0, 180+1, 10):
    for sn_lon in range(0, 180, 10):
        sn_x = sn_lon * 240 * ps
        h_idx = np.round((sn_lon - -180) // 10, decimals = 1)
        print()
        print(f'Computing for sn_lon: {sn_lon} (h_idx: {h_idx:02d}),  sn_x: {sn_x}')

        crossed_180o = False

        # Step in latitude in 1-degree steps
        # for sn_lat in range(1, 90):
        # for sn_lat in range(0, 90):
        for sn_lat in range(0, 90):
            sn_y = sn_lat * 240 * ps
            # v_idx = np.round((90 - sn_lat) / 10, decimals=1)
            vd_idx = 90 - sn_lat

            lat, lon, _ = sn2ll.TransformPoint(sn_x, sn_y)

            if lon < 0 or lon > 180.0 or lat > 90.0:
                print(f'lon crossed 180o moving vert for {h_idx} {vd_idx}')
                crossed_180o = True
                # We have crossed 180o.
                crossed_180o = True

                # Back off and step in one-sn_pixel increments
                sn_lat -= 1

                for sn_j in range(sn_lat * 240, (sn_lat + 10) * 240):
                    sn_y = sn_j * ps
                    lat, lon, _ = sn2ll.TransformPoint(sn_x, sn_y)

                    if lon < 0 or lon > 180.0 or lat > 90.0:
                        # We have crossed 180o.  Back off to get last-valid sn_j
                        sn_j -= 1
                        sn_y = sn_j * ps
                        lat, lon, _ = sn2ll.TransformPoint(sn_x, sn_y)
                        # Use this lat, and use 180 as lon
                        lon = 180.000
                        # print(f'setting vert_extend for {h_idx}, {vd_idx}  {lon:.5f} {lat:.5f}')
                        vert_extend_lat[h_idx, vd_idx] = lat
                        vert_extend_lon[h_idx, vd_idx] = lon

                        break

            else:
                # print(f'Setting vert_bounds for {h_idx}, {vd_idx}  {lon:.5f} {lat:.5f}')
                vert_bounds_lat[h_idx, vd_idx] = lat
                vert_bounds_lon[h_idx, vd_idx] = lon

            if crossed_180o:
                break

    vert_dict['vert_bounds_lat'] = vert_bounds_lat
    vert_dict['vert_bounds_lon'] = vert_bounds_lon
    vert_dict['vert_extend_lat'] = vert_extend_lat
    vert_dict['vert_extend_lon'] = vert_extend_lon
    return vert_dict


def fill_nonUR_quadrants_vert(vert_dict):
    """Given the UR quadrant, reflect on y-axis to get UL,
    then reflect on x-axis to get LL and LR"""
    vert_bounds_lat = vert_dict['vert_bounds_lat']
    vert_bounds_lon = vert_dict['vert_bounds_lon']
    vert_extend_lat = vert_dict['vert_extend_lat']
    vert_extend_lon = vert_dict['vert_extend_lon']

    print('Finished computing vertical bounds for UR quadrant...')
    # Now, flip along y-axis to fill UL quadrant

    # Flip on y-axis to fill h00-h17 v00-v08
    # Loop along each 10-degree step in x
    for hidx_ur in range(19, 36+1):
        # Mirror on y-axis, so 19->17, 20->16, etc
        hidx_ul = 36 - hidx_ur

        for vidx_ur in range(0, 90+1):
            vidx_ul = vidx_ur
            vert_bounds_lat[hidx_ul, vidx_ul] = vert_bounds_lat[hidx_ur, vidx_ur]
            vert_bounds_lon[hidx_ul, vidx_ul] = -vert_bounds_lon[hidx_ur, vidx_ur]
            vert_extend_lat[hidx_ul, vidx_ul] = vert_extend_lat[hidx_ur, vidx_ur]
            vert_extend_lon[hidx_ul, vidx_ul] = -vert_extend_lon[hidx_ur, vidx_ur]

    for hidx_u in range(0, 36+1):
        hidx_l = hidx_u

        for vidx_u in range(0,  90+1):
            vidx_l = 180 - vidx_u

            vert_bounds_lat[hidx_l, vidx_l] = -vert_bounds_lat[hidx_u, vidx_u]
            vert_bounds_lon[hidx_l, vidx_l] = vert_bounds_lon[hidx_u, vidx_u]
            vert_extend_lat[hidx_l, vidx_l] = -vert_extend_lat[hidx_u, vidx_u]
            vert_extend_lon[hidx_l, vidx_l] = vert_extend_lon[hidx_u, vidx_u]

    vert_dict['vert_bounds_lat'] = vert_bounds_lat
    vert_dict['vert_bounds_lon'] = vert_bounds_lon
    vert_dict['vert_extend_lat'] = vert_extend_lat
    vert_dict['vert_extend_lon'] = vert_extend_lon

    return vert_dict


def print_vert_bounds_UR(vert_dict):
    """Print only the Upper Right quadrant values of the vertical bounds"""
    vert_bounds_lat = vert_dict['vert_bounds_lat']
    vert_bounds_lon = vert_dict['vert_bounds_lon']
    vert_extend_lat = vert_dict['vert_extend_lat']
    vert_extend_lon = vert_dict['vert_extend_lon']
    print('===================================')

    print('Only Upper Right Quadrant...')
    print('*** vert_bounds ***')
    print('Latitudes:')

    # Print the header
    print('                       ', end='')  # Spacer
    for i in range(18, 36+1):
        hidx = (vert_bounds_lon[i, 90] - -180) / 10
        print(f' h{hidx:4.1f} ', end='')
    print()

    for j in range(90 + 1):
        # vidx = (90 - np.round(vert_bounds_lat[18, j], decimals=1)) // 10
        vidx = 90 - np.round(vert_bounds_lat[18, j], decimals=0)
        vlat = np.round(vert_bounds_lat[18, j], decimals=1)
        print(f'j={j:2d} vlat:{vlat:4.1f} v{vidx:4.1f}:  ', end='')
        for i in range(18, 36+1):
            if not np.isnan(vert_bounds_lat[i, j]):
                print(f'{vert_bounds_lat[i, j]:6.2f} ', end='')
            elif not np.isnan(vert_extend_lat[i, j]):
                print(f'{vert_extend_lat[i, j]:6.2f} ', end='')
            else:
                print(f'{vert_bounds_lat[i, j]:6.2f} ', end='')
        print()

    print()
    print('Longitudes:')
    # for j in range(9 + 1):
    for j in range(90 + 1):
        # vidx = (90 - np.round(vert_bounds_lat[18, j], decimals=1)) // 10
        vidx = 90 - np.round(vert_bounds_lat[18, j], decimals=1)
        vlat = np.round(vert_bounds_lat[18, j], decimals=1)
        print(f'j={j:2d} vlat:{vlat:4.1f} v{vidx:4.1f}:  ', end='')
        for i in range(18, 36+1):
            if not np.isnan(vert_bounds_lat[i, j]):
                print(f'{vert_bounds_lon[i, j]:6.2f} ', end='')
            elif not np.isnan(vert_extend_lat[i, j]):
                print(f'{vert_extend_lon[i, j]:6.2f} ', end='')
            else:
                print(f'{vert_bounds_lon[i, j]:6.2f} ', end='')
        print()


def print_vert_bounds(vert_dict):
    """Print the vertical bounds indices (low res)"""
    vert_bounds_lat = vert_dict['vert_bounds_lat']
    vert_bounds_lon = vert_dict['vert_bounds_lon']
    vert_extend_lat = vert_dict['vert_extend_lat']
    vert_extend_lon = vert_dict['vert_extend_lon']
    print('===================================')
    print()
    print()
    print('Full latitudes')
    # Print the header
    print('                        ', end='')  # Spacer
    for i in range(0, 36+1):
        hidx = np.round((vert_bounds_lon[i, 90] - -180) / 10, decimals=0)
        print(f' h{hidx:02.0f}', end='')
    print()

    # for j in range(9 + 1):
    for j in range(180 + 1):
        vidx = (90 - np.round(vert_bounds_lat[18, j], decimals=1)) / 10
        vlat = np.round(vert_bounds_lat[18, j], decimals=1)
        print(f'j={j:3d} vlat:{vlat:5.1f} v{vidx:4.1f}:  ', end='')
        for i in range(0, 36+1):
            if not np.isnan(vert_bounds_lat[i, j]):
                print(f'{vert_bounds_lat[i, j]:3.0f} ', end='')
            elif not np.isnan(vert_extend_lat[i, j]):
                print(f'{vert_extend_lat[i, j]:3.0f} ', end='')
            else:
                print(f'{vert_bounds_lat[i, j]:3.0f} ', end='')
        print()

    print('Full longitudes')
    for j in range(180 + 1):
        vidx = (90 - np.round(vert_bounds_lat[18, j], decimals=1)) / 10
        vlat = np.round(vert_bounds_lat[18, j], decimals=1)
        print(f'j={j:3d} vlat:{vlat:5.1f} v{vidx:4.1f}: ', end='')
        for i in range(0, 36+1):
            if not np.isnan(vert_bounds_lon[i, j]):
                print(f'{vert_bounds_lon[i, j]:4.0f}', end='')
            elif not np.isnan(vert_extend_lon[i, j]):
                print(f'{vert_extend_lon[i, j]:4.0f}', end='')
            else:
                print(f'{vert_bounds_lon[i, j]:4.0f}', end='')
        print()

    print('===================================')

    print(f'Start the geospatial_bounds polygon in the corner that is guaranteed to exist,')
    print('i.e., the one closest to 0N, 0E.  Then, proceed counterclockwise')
    print('  In UL quadrant, start geospatial bounds in LR, then UR, UL, LL, back to LR')
    print('  In UR quadrant, start geospatial bounds in LL, then LR, UR, UL, back to LL')
    print('  In LR quadrant, start geospatial bounds in UL, then LL, LR, UR, back to UL')
    print('  In LL quadrant, start geospatial bounds in UR, then UL, LL, LR, back to UR')

    print()


def get_tile_h_v(tileID):
    """Return the integer h and v values for this tileID"""
    h = int(tileID[1:3])
    v = int(tileID[4:6])

    return h, v


def format_vertex(vertlat, vertlon):
    """Prepare the vertex tuple"""
    # Note: adding 0 to a number prevents negative zero, e.g.:  "-0.0000"
    vertex_tuple = f'{0 + vertlat:.5f} {0 + vertlon:.5f}'
    return vertex_tuple


def get_LR_to_UR(tileID, is_origin=False, is_endpoint=False, verbose=True):
    """Return the vertical indices..."""
    vert_bounds_lat = vert_dict['vert_bounds_lat']
    vert_bounds_lon = vert_dict['vert_bounds_lon']
    vert_extend_lat = vert_dict['vert_extend_lat']
    vert_extend_lon = vert_dict['vert_extend_lon']

    h, v = get_tile_h_v(tileID)
    # Tiles are defined at UL, so
    #   LR is h+1, v+1
    vmult = 10  # This is 10 because this is vertical step

    hidx = h + 1
    vstart = (v + 1) * vmult
    vstop = v * vmult
    vstep = -1

    list_of_vertices = []

    found_true_bounds = False

    for vidx in range(vstart, vstop + vstep, vstep):
        if not np.isnan(vert_bounds_lat[hidx, vidx]):
            if verbose:
                print(f'LR2UR: {hidx}, {vidx}: {vert_bounds_lat[hidx, vidx]:.4f} {vert_bounds_lon[hidx, vidx]:.4f}')
            vertex = format_vertex(vert_bounds_lat[hidx, vidx], vert_bounds_lon[hidx, vidx])
            list_of_vertices.append(vertex)
            found_true_bounds = True
        elif not np.isnan(vert_extend_lat[hidx, vidx]):
            if verbose:
                print(f'LR2UR: {hidx}, {vidx}: {vert_extend_lat[hidx, vidx]:.4f} {vert_extend_lon[hidx, vidx]:.4f} (extend)')
            vertex = format_vertex(vert_extend_lat[hidx, vidx], vert_extend_lon[hidx, vidx])
            list_of_vertices.append(vertex)
        else:
            if verbose:
                print(f'LR2UR: {hidx}, {vidx}: {vert_bounds_lat[hidx, vidx]:.4f} {vert_bounds_lon[hidx, vidx]:.4f} (nan)')
            vertex = format_vertex(vert_bounds_lat[hidx, vidx], vert_bounds_lon[hidx, vidx])
            list_of_vertices.append(vertex)

    # Valid tiles must have non-extend values at their origin
    if is_origin and not found_true_bounds:
        list_of_vertices = []

    return list_of_vertices


def get_UR_to_UL(tileID, is_origin=False, is_endpoint=False, verbose=True):
    """Return the vertical indices..."""
    horiz_bounds_lat = horiz_dict['horiz_bounds_lat']
    horiz_bounds_lon = horiz_dict['horiz_bounds_lon']
    horiz_extend_lat = horiz_dict['horiz_extend_lat']
    horiz_extend_lon = horiz_dict['horiz_extend_lon']
    h, v = get_tile_h_v(tileID)
    # Tiles are defined at UL, so
    #   UR is h+1, v

    vmult = 1  # This is 1 because this is horizontal step

    vidx = v * vmult

    hstart = h + 1
    hstop = h
    hstep = -1

    list_of_vertices = []

    found_true_bounds = False

    for hidx in range(hstart, hstop + hstep, hstep):
        if not np.isnan(horiz_bounds_lat[hidx, vidx]):
            if verbose:
                print(f'UR2UL: {hidx}, {vidx}: {horiz_bounds_lat[hidx, vidx]:.4f} {horiz_bounds_lon[hidx, vidx]:.4f}')
            vertex = format_vertex(horiz_bounds_lat[hidx, vidx], horiz_bounds_lon[hidx, vidx])
            list_of_vertices.append(vertex)
            found_true_bounds = True
        elif not np.isnan(horiz_extend_lat[hidx, vidx]):
            if verbose:
                print(f'UR2UL: {hidx}, {vidx}: {horiz_extend_lat[hidx, vidx]:.4f} {horiz_extend_lon[hidx, vidx]:.4f} (extend)')
            vertex = format_vertex(horiz_extend_lat[hidx, vidx], horiz_extend_lon[hidx, vidx])
            list_of_vertices.append(vertex)
        else:
            if verbose:
                print(f'UR2UL: {hidx}, {vidx}: {horiz_bounds_lat[hidx, vidx]:.4f} {horiz_bounds_lon[hidx, vidx]:.4f} (nan)')
            vertex = format_vertex(horiz_bounds_lat[hidx, vidx], horiz_bounds_lon[hidx, vidx])
            list_of_vertices.append(vertex)

    # Valid tiles must have non-extend values at their origin
    if is_origin and not found_true_bounds:
        list_of_vertices = []

    return list_of_vertices


def get_UL_to_LL(tileID, is_origin=False, is_endpoint=False, verbose=True):
    """Return the vertical indices..."""
    vert_bounds_lat = vert_dict['vert_bounds_lat']
    vert_bounds_lon = vert_dict['vert_bounds_lon']
    vert_extend_lat = vert_dict['vert_extend_lat']
    vert_extend_lon = vert_dict['vert_extend_lon']
    h, v = get_tile_h_v(tileID)
    # Tiles are defined at UL, so
    #   LR is h+1, v+1
    vmult = 10  # This is 10 because this is vertical step

    hidx = h  # hidx is h because left
    vstart = v * vmult
    vstop = (v + 1) * vmult
    vstep = 1

    list_of_vertices = []
    found_true_bounds = False

    for vidx in range(vstart, vstop + vstep, vstep):
        if not np.isnan(vert_bounds_lat[hidx, vidx]):
            if verbose:
                print(f'UL2LL: {hidx}, {vidx}: {vert_bounds_lat[hidx, vidx]:.4f} {vert_bounds_lon[hidx, vidx]:.4f}')
            vertex = format_vertex(vert_bounds_lat[hidx, vidx], vert_bounds_lon[hidx, vidx])
            list_of_vertices.append(vertex)
            found_true_bounds = True
        elif not np.isnan(vert_extend_lat[hidx, vidx]):
            if verbose:
                print(f'UL2LL: {hidx}, {vidx}: {vert_extend_lat[hidx, vidx]:.4f} {vert_extend_lon[hidx, vidx]:.4f} (extend)')
            vertex = format_vertex(vert_extend_lat[hidx, vidx], vert_extend_lon[hidx, vidx])
            list_of_vertices.append(vertex)
        else:
            if verbose:
                print(f'UL2LL: {hidx}, {vidx}: {vert_bounds_lat[hidx, vidx]:.4f} {vert_bounds_lon[hidx, vidx]:.4f} (nan)')
            vertex = format_vertex(vert_bounds_lat[hidx, vidx], vert_bounds_lon[hidx, vidx])
            list_of_vertices.append(vertex)

    # Valid tiles must have non-extend values at their origin
    if is_origin and not found_true_bounds:
        list_of_vertices = []

    return list_of_vertices


def get_LL_to_LR(tileID, is_origin=False, is_endpoint=False, verbose=True):
    """Return the vertical indices..."""
    horiz_bounds_lat = horiz_dict['horiz_bounds_lat']
    horiz_bounds_lon = horiz_dict['horiz_bounds_lon']
    horiz_extend_lat = horiz_dict['horiz_extend_lat']
    horiz_extend_lon = horiz_dict['horiz_extend_lon']
    h, v = get_tile_h_v(tileID)
    # Tiles are defined at UL, so
    #   UR is h+1, v

    vmult = 1  # This is 1 because this is horizontal step

    vidx = (v + 1) * vmult

    hstart = h
    hstop = h + 1
    hstep = 1

    list_of_vertices = []

    found_true_bounds = False
    for hidx in range(hstart, hstop + hstep, hstep):
        if not np.isnan(horiz_bounds_lat[hidx, vidx]):
            if verbose:
                print(f'LL2LR: {hidx}, {vidx}: {horiz_bounds_lat[hidx, vidx]:.4f} {horiz_bounds_lon[hidx, vidx]:.4f}')
            vertex = format_vertex(horiz_bounds_lat[hidx, vidx], horiz_bounds_lon[hidx, vidx])
            list_of_vertices.append(vertex)
            found_true_bounds = True
        elif not np.isnan(horiz_extend_lat[hidx, vidx]):
            if verbose:
                print(f'LL2LR: {hidx}, {vidx}: {horiz_extend_lat[hidx, vidx]:.4f} {horiz_extend_lon[hidx, vidx]:.4f} (extend)')
            vertex = format_vertex(horiz_extend_lat[hidx, vidx], horiz_extend_lon[hidx, vidx])
            list_of_vertices.append(vertex)
        else:
            if verbose:
                print(f'LL2LR: {hidx}, {vidx}: {horiz_bounds_lat[hidx, vidx]:.4f} {horiz_bounds_lon[hidx, vidx]:.4f} (nan)')
            vertex = format_vertex(horiz_bounds_lat[hidx, vidx], horiz_bounds_lon[hidx, vidx])
            list_of_vertices.append(vertex)

    # Valid tiles must have non-extend values at their origin
    if is_origin and not found_true_bounds:
        list_of_vertices = []

    return list_of_vertices


def compute_sample_polygon(tileID='h09v05'):
    """ 'Manually' run through the calculations for a single tile's vertices"""
    print(f'Sample polygon: {tileID}...')
    print('  Assuming this is UL, so start with LR corner.')
    polygon = []

    print('  In LR quadrant, start geospatial bounds in UL, then LL, LR, UR, back to UL')
    # Add from LR to UR (vertical)
    vertices = get_LR_to_UR(tileID, is_origin=True)
    print()
    vertices = get_UR_to_UL(tileID)
    print()
    vertices = get_UL_to_LL(tileID)
    print()
    vertices = get_LL_to_LR(tileID, is_endpoint=True)
    print()


def get_quadrant(tileID):
    """Return the quadrant of the modsinu grid for this tile"""
    h, v = get_tile_h_v(tileID)
    if h <= 18:
        if v <= 9:
          quadrant = 'UL'
        else:
          quadrant = 'LL'
    else:
        if v <= 9:
          quadrant = 'UR'
        else:
          quadrant = 'LR'

    return quadrant


def reduce_vertex_list(vertex_list, verbose=True):
    """Remove duplicates and NaNs from this list
      E.g:
        Original vertex_list...  New vertex_list...
          30.00000 -103.92305      30.00000 -103.92305
          30.00000 -92.37604       30.00000 -92.37604
          30.00000 -92.37604
          31.00000 -93.33067       31.00000 -93.33067
          32.00000 -94.33427       32.00000 -94.33427
          33.00000 -95.38906       33.00000 -95.38906
          34.00000 -96.49744       34.00000 -96.49744
          35.00000 -97.66197       35.00000 -97.66197
          36.00000 -98.88544       36.00000 -98.88544
          37.00000 -100.17085      37.00000 -100.17085
          38.00000 -101.52146      38.00000 -101.52146
          39.00000 -102.94077      39.00000 -102.94077
          40.00000 -104.43258      40.00000 -104.43258
          40.00000 -104.43258
          40.00000 -117.48666      40.00000 -117.48666
          40.00000 -117.48666
          39.00000 -115.80836      39.00000 -115.80836
          38.00000 -114.21164      38.00000 -114.21164
          37.00000 -112.69221      37.00000 -112.69221
          36.00000 -111.24612      36.00000 -111.24612
          35.00000 -109.86971      35.00000 -109.86971
          34.00000 -108.55962      34.00000 -108.55962
          33.00000 -107.31270      33.00000 -107.31270
          32.00000 -106.12606      32.00000 -106.12606
          31.00000 -104.99701      31.00000 -104.99701
          30.00000 -103.92305      30.00000 -103.92305
  """
    try:
        new_vertex_list = [vertex_list[0]]
        # Return empty list if the first is NaN
        if 'nan' in vertex_list[0]:
            if verbose:
                print('Returning empty vertex list')
            return []
    except IndexError:
        # If we don't have a first item, return what was passed in
        return vertex_list

    idx_new = 0
    for vertex in vertex_list[1:]:
        # If we have a new vertex, add it
        # Otherwise, don't add anything
        if vertex != new_vertex_list[idx_new] and not 'nan' in vertex:
            new_vertex_list.append(vertex)
            idx_new += 1

    if len(new_vertex_list) > 0:
        try:
            assert new_vertex_list[0] == new_vertex_list[-1]
        except AssertionError as err:
            print('need to handle different first/last vertices:')
            print(f'{err}')
            breakpoint()

    # If 'extend' points are used on both sides connected to close-corner vertex,
    #  then there will be three (more?) vertices in a row with longitude=180 (or -180)
    bad_vertices = []
    for idx in range(1, len(new_vertex_list)-1):
        # print(f'  v-1: {new_vertex_list[idx-1]}')
        # print(f'    v: {new_vertex_list[idx]}')
        # print(f'  v+1: {new_vertex_list[idx+1]}')

        lat_str_vm1, lon_str_vm1 = new_vertex_list[idx-1].split(' ')
        lat_vm1 = float(lat_str_vm1)
        lon_vm1 = float(lon_str_vm1)

        lat_str_v, lon_str_v = new_vertex_list[idx].split(' ')
        lat_v = float(lat_str_v)
        lon_v = float(lon_str_v)

        lat_str_vp1, lon_str_vp1 = new_vertex_list[idx+1].split(' ')
        lat_vp1 = float(lat_str_vp1)
        lon_vp1 = float(lon_str_vp1)

        if np.all(np.isclose((lon_vm1, lon_v, lon_vp1), 180)):
            # print(f'  Should drop: {new_vertex_list[idx]}')
            bad_vertices.append(new_vertex_list[idx])
        elif np.all(np.isclose((lon_vm1, lon_v, lon_vp1), -180)):
            # print(f'  Should drop: {new_vertex_list[idx]}')
            bad_vertices.append(new_vertex_list[idx])

        # print(f'   {np.all((lon_vm1, lon_v, lon_vp1) == 180)=}')
        # print(f'   {np.all((lon_vm1, lon_v, lon_vp1) == (180, 180, 180))=}')
        # print()

    for bad_vertex in bad_vertices:
        print(f'  Removing {bad_vertex} from {tileID}')
        #breakpoint()
        new_vertex_list.remove(bad_vertex)
        #print('  Dropped!')
        #breakpoint()

    if len(bad_vertices) > 0:
        print()

    return new_vertex_list


def get_minmax_str(tileID, vertex_list):
    """Compute the string equiv to lines in: sn_bound_10deg.txt"""
    h, v = get_tile_h_v(tileID)
    minmax_str = f'{v:3d} {h:3d} '

    if len(vertex_list) == 0:
        minmax_str += ' -999.0000  -999.0000  -99.0000  -99.0000'
    else:
        # Parse the string
        lonmin = 9999
        latmin = 9999
        lonmax = -9999
        latmax = -9999
        for vertex in vertex_list:
            lat_str, lon_str = vertex.split(' ')
            lat = float(lat_str)
            lon = float(lon_str)

            lonmin = min(lonmin, lon)
            lonmax = max(lonmax, lon)

            latmin = min(latmin, lat)
            latmax = max(latmax, lat)

        minmax_str += f' {lonmin:9.4f}  {lonmax:9.4f}  {latmin:8.4f}  {latmax:8.4f}'

    return minmax_str


def format_polygon_str(vertex_list):
    """Create a string compatible with netCDF attribute "geospatial_bounds_str"
    of the form comma-separated sets of space-separated lat/lon vertices:
        POLYGON((lat1 lon1,lat2 lon2,lat3 lon3,...,latN lonN))
    eg:
        POLYGON((60.0000 -180.0000,70.0000 -180.0000,70.0000 -119.9833,60.0000 -119.9833,60.0000 -180.0000))
    Note: For the closed polygon, (lat1 lon1) == (lanN lonN)
    """
    if len(vertex_list) == 0:
        return 'POLYGON(())'

    poly_str = 'POLYGON(('
    # Hmm.  I guess I could have used list comprehension here...
    poly_str += vertex_list[0]
    for vertex in vertex_list[1:]:
        poly_str += ','
        poly_str += vertex

    poly_str += '))'

    return poly_str


def compute_polygon_str(tileID, verbose=True):
    """ Return the POLYGON string for this tileID

    Vertices are calculated in counter-clockwise order

    Note: tileIDs are identified by the upper-left vertex

    geospatial_bounds_str is of the form [note spaces between x,y and commas between points]:
      POLYGON((llx lly, ulx uly, urx ury, lrx lry, llx lly))

    E.g. the example from ACDD-1.3 is:
      Example: 'POLYGON ((40.26 -111.29, 41.26 -111.29, 41.26 -110.29, 40.26 -110.29, 40.26 -111.29))'

    Here, we use two vertices along horizontal edges (top and bottom of) grid cell
      and up to ten vertices along vertical edges (left and right) of grid cell.

    If a grid cell is a NaN at its starting vertex, eg the LR vertex for h00v00,
      then that grid cell is off-earth.

    tiles in Upper Left quadrant always have a LR value, so start there
    tiles in Upper Right always have -- and therefore start with -- LL
    tiles in Lower Right start with UL
    tiles in Lower Left start with UR
    """

    # Determine the quadrant, which determines which set of vertices to
    #   calculate first.
    quadrant = get_quadrant(tileID)

    if verbose:
        print(f'Computing polygon: {tileID}...')

    vertex_list = []

    if quadrant == 'LR':
        vertex_list.extend(get_UL_to_LL(tileID, is_origin=True, verbose=verbose))
        vertex_list.extend(get_LL_to_LR(tileID, verbose=verbose))
        vertex_list.extend(get_LR_to_UR(tileID, verbose=verbose))
        vertex_list.extend(get_UR_to_UL(tileID, is_endpoint=True, verbose=verbose))
    elif quadrant == 'UR':
        vertex_list.extend(get_LL_to_LR(tileID, is_origin=True, verbose=verbose))
        vertex_list.extend(get_LR_to_UR(tileID, verbose=verbose))
        vertex_list.extend(get_UR_to_UL(tileID, verbose=verbose))
        vertex_list.extend(get_UL_to_LL(tileID, is_endpoint=True, verbose=verbose))
    elif quadrant == 'UL':
        vertex_list.extend(get_LR_to_UR(tileID, is_origin=True, verbose=verbose))
        vertex_list.extend(get_UR_to_UL(tileID, verbose=verbose))
        vertex_list.extend(get_UL_to_LL(tileID, verbose=verbose))
        vertex_list.extend(get_LL_to_LR(tileID, is_endpoint=True, verbose=verbose))
    elif quadrant == 'LL':
        vertex_list.extend(get_UR_to_UL(tileID, is_origin=True, verbose=verbose))
        vertex_list.extend(get_UL_to_LL(tileID, verbose=verbose))
        vertex_list.extend(get_LL_to_LR(tileID, verbose=verbose))
        vertex_list.extend(get_LR_to_UR(tileID, is_endpoint=True, verbose=verbose))
    else:
        raise RuntimeError(f'quadrant not recognized: {quadrant}')

    # Check vertex_list...
    if verbose:
        print('Original vertex_list...')
        for vertex in vertex_list:
            print(f'  {vertex}')

    vertex_list = reduce_vertex_list(vertex_list, verbose=verbose)
    # vertex_list = reduce_vertex_list(vertex_list, verbose=tileID=='h30v13')

    # On a latlon projection, the bounding box looks wrong if we don't
    #   repeat the vertex at the pole with a mathematically-equivalent
    #   vertex at the -180/180 longitude line
    if tileID == 'h17v00':
        # For NW tile at North Pole, need to add 90, -180 after 90, 0
        new_vertex_list = []
        for vertex in vertex_list:
            # Add new vertex *after* existing pole vertex
            new_vertex_list.append(vertex)
            if vertex[:7] == '90.0000':
                pole_vertex = '90.00000 -180.00000'
                # pole_vertex = '89.99999 -179.99999'
                new_vertex_list.append(pole_vertex)
                print(f'Added {pole_vertex} to vertext list for {tileID}')
        vertex_list = new_vertex_list
    elif tileID == 'h18v00':
        # For NE tile at North Pole, need to add 90, 180 before 90, 0
        new_vertex_list = []
        for vertex in vertex_list:
            # Add new vertex *before* existing pole vertex
            if vertex[:7] == '90.0000':
                pole_vertex = '90.00000 180.00000'
                # pole_vertex = '89.99999 179.99999'
                new_vertex_list.append(pole_vertex)
                print(f'Added {pole_vertex} to vertext list for {tileID}')
            new_vertex_list.append(vertex)
        vertex_list = new_vertex_list
    elif tileID == 'h17v17':
        # For SW tile at South Pole, need to add -90, -180 before -90, 0
        new_vertex_list = []
        for vertex in vertex_list:
            # Add new vertex *before* existing pole vertex
            if vertex[:8] == '-90.0000':
                pole_vertex = '-90.00000 -180.00000'
                # pole_vertex = '-89.99999 -179.99999'
                new_vertex_list.append(pole_vertex)
                print(f'Added {pole_vertex} to vertext list for {tileID}')
            new_vertex_list.append(vertex)
        vertex_list = new_vertex_list
    elif tileID == 'h18v17':
        # For SE tile at South Pole, need to add -90, 180 after -90, 0
        new_vertex_list = []
        for vertex in vertex_list:
            # Add new vertex *after* existing pole vertex
            new_vertex_list.append(vertex)
            if vertex[:8] == '-90.0000':
                pole_vertex = '-90.00000 180.00000'
                # pole_vertex = '-89.99999 179.99999'
                new_vertex_list.append(pole_vertex)
                print(f'Added {pole_vertex} to vertext list for {tileID}')
        vertex_list = new_vertex_list

    # Verify the pole tile vertex addition
    poletiles = ('h17v00', 'h18v00', 'h17v17', 'h18v17')
    if tileID in poletiles:
        print(f'Check vertex_list: {tileID}')
        pp(vertex_list)
        breakpoint()

    if verbose:
        print('New vertex_list...')
        for vertex in vertex_list:
            print(f'  {vertex}')

    minmax_str = get_minmax_str(tileID, vertex_list)
    if verbose:
        print(f'{minmax_str}')

    polygon_str = format_polygon_str(vertex_list)

    return minmax_str, polygon_str


if __name__ == '__main__':
    print('Calculating the bounding polygons for the MODIS sinusoidal grid')

    horiz_dict = compute_horizontal_bounds_UR()
    horiz_dict = fill_nonUR_quadrants_horiz(horiz_dict)

    print_horiz_bounds_UR(horiz_dict)
    print_horiz_bounds(horiz_dict)

    vert_dict = compute_vert_bounds_UR()
    vert_dict = fill_nonUR_quadrants_vert(vert_dict)

    print('check edge cases...eg')
    print('check 36, 0')
    print('check 36, 9    36, 90')
    print('check 18, 9    36, 90')

    print_vert_bounds_UR(vert_dict)
    print_vert_bounds(vert_dict)

    # compute_sample_polygon()

    # Run sample polygons
    # compute_polygon_str('h09v05')  # typical tile
    # compute_polygon_str('h30v13')  # tile that crosses 180
    # compute_polygon_str('h32v17')  # off-earth tile
    # compute_polygon_str('h14v00')  # very small tile

    # # Edit here if you would like to manually run cases
    # print('Running UR tile...')
    # compute_polygon_str('h14v00')  # challenging UR tile
    # compute_polygon_str('h21v00')  # equivalent UL tile
    # print('Any more manual compute_polygon_str() before ending?')
    # print('  Use:  compute_polygon_str( tileid )')
    # breakpoint()

    # Let's run them all!
    minmax_dict = {}
    polygon_dict = {}
    valid_tile_count = 0
    for v in range(18):
        for h in range(36):
            tileID = f'h{h:02d}v{v:02d}'
            mm_str, poly_str = compute_polygon_str(tileID, verbose=False)
            # mm_str, poly_str = compute_polygon_str(tileID, verbose=tileID == 'h30v13')
            minmax_dict[tileID] = mm_str
            # Only add polygons for valid tiles
            if '-999' not in mm_str:
                polygon_dict[tileID] = poly_str
                valid_tile_count += 1
                #print(f'mm_str: {mm_str}')
                #print(f'poly_str: {poly_str}')
                #breakpoint()

            # if tileID == 'h30v13':
            #     print('AAAHHHHGGGHHH')
            #     breakpoint()


    print(f'Ran all the polygons; number of valid tiles: {valid_tile_count}')

    minmax_fn = 'modis_tile_lonlat_bounds.txt'
    with open(minmax_fn, 'w') as f:
        # Write the same header as sn_bound_10deg.txt
        #   From: https://modis-land.gsfc.nasa.gov/MODLAND_grid.html
        print(' iv  ih    lon_min    lon_max   lat_min   lat_max', file=f)
        for _, minmax_str in minmax_dict.items():
            print(minmax_str, file=f)
    print(f'Wrote: {minmax_fn}')

    polygon_fn = 'modis_tile_geospatial_bounds.yml'
    with open(polygon_fn, 'w') as f:
        yaml.safe_dump(polygon_dict, f)
    print(f'Wrote: {polygon_fn}')

    """
    # Note: This is how the `netcdf.py` code expects to get information:
    def add_geospatial_info(tile_id, nc_dataset):
        hid, vid = get_tiletuple_from_arg(tile_id)
        xmin, xmax, ymin, ymax = get_xy_minmax(hid, vid)
        is_valid_tileID, lon_min, lon_max, lat_min, lat_max = look_up_latlon_minmax(
            hid, vid
        )
        geotransform_string = get_geotransform(hid, vid)
        geospatial_bounds_string = get_geospatial_bounds_latlon(hid, vid)

        add_nc_coordinate_values(xmin, xmax, ymin, ymax, nc_dataset)
        nc_dataset.variables["crs"].GeoTransform = geotransform_string
        nc_dataset.geospatial_bounds = geospatial_bounds_string
        nc_dataset.geospatial_lat_min = lat_min
        nc_dataset.geospatial_lat_max = lat_max
        nc_dataset.geospatial_lon_min = lon_min
        nc_dataset.geospatial_lon_max = lon_max
    """
