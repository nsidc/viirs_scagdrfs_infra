"""Create a shapefile with all of the polgons in it
Usage:
    Run this after generating the list of polgyon vertices:
        python   calc_gsbounds_vertices2.py
      which yields:
        modis_tile_geospatial_bounds.yml
    Run this code with:
      python create_allpoly_shpfile.py
    which will generate individual shapefiles for each tile in:
      modsinu_latlon_bounds_files/
    and a single shapefile with all of the tile boundaries in:
       MODIS_tile_boundaries.shp.zip
"""

import geopandas as gpd
import os
import sys
import yaml


def create_allpolys_shpfile(fn):
    """Create a shapefile with all of the tiles in fn"""
    with open(fn) as f:
        poly_dict = yaml.safe_load(f)

    tile_shpfile_dir = 'modsinu_latlon_bounds_files'
    os.makedirs(tile_shpfile_dir, exist_ok=True)

    fn_list = []
    print()
    for tileID in poly_dict.keys():
        print(f' {tileID=}')
        fn_poly_cps = f'latlon_poly_{tileID}.shp.zip'
        fn_poly_here = f'{tile_shpfile_dir}/modsinu_latlon_bounds_{tileID}.shp.zip'
        if not os.path.isfile(fn_poly_here):
            os.system(f'python create_polygon_shpfile.py {tileID} modis_tile_geospatial_bounds.yml')
            os.system(f'mv -v {fn_poly_cps} {fn_poly_here}')
        fn_list.append(fn_poly_here)

    print('Generating shpfile_list...')
    shpfile_list = []
    for idx, shp_fn in enumerate(fn_list):
        print(f' Attempting to append {idx}: {shp_fn}')
        shpfile_list.append(gpd.read_file(shp_fn))

    print('Concatenating shapefiles...')
    global_gpd = gpd.pd.concat(shpfile_list)

    ofn = 'MODIS_tile_boundaries.shp.zip'
    print(f'Writing: {ofn}...', end='')
    global_gpd.to_file(ofn)

    print(f'\nCode complete')


if __name__ == '__main__':
    try:
        fn_polygons = sys.argv[1]
    except IndexError:
        fn_polygons = './modis_tile_geospatial_bounds.yml'

    create_allpolys_shpfile(fn_polygons)
