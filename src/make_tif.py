import numpy as np
from pathlib import Path
from osgeo import gdal, osr

from src.util import (
    get_info_from_bip_file,
)


MODSINU_WKT_STRING = 'PROJCS[' \
        '"Sinusoidal",' \
        'GEOGCS["GCS_Unknown",' \
        'DATUM["D_unknown",SPHEROID["Unknown",6371007.181,0]],' \
        'PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]],' \
        'PROJECTION["Sinusoidal"],' \
        'PARAMETER["central_meridian",0],' \
        'PARAMETER["false_easting",0],' \
        'PARAMETER["false_northing",0],' \
        'UNIT["Meter",1]]'

GEOTIFF_OPTIONS = ["COMPRESS=DEFLATE"]

MODSINU_500M_LENGTH = 463.31271656938424


def write_geotiff_via_gdal(
    fp_geotiff,
    data,
    geotransform=None,
    grid_corners=None,
    pixel_size=None,
    modsinu_tile=None,
    nodata_value=None,
    color_table=None,
):
    """Use GDAL to write a geotiff"""
    dtype = data.dtype
    gdal_dtype = None
    nodata_default = None
    if dtype == np.uint8:
        gdal_dtype = gdal.GDT_Byte
        nodata_default = 255
    elif dtype == np.uint16:
        gdal_dtype = gdal.GDT_UInt16
        nodata_default = 65535
    elif dtype == np.float32:
        gdal_dtype = gdal.GDT_Float32
        nodata_default = None
    else:
        raise ValueError(f'Unknown data type for geotiff: {dtype}')

    if nodata_value is None:
        nodata_value = nodata_default

    # Determine the GeoTransform from: string, corners, tileID
    ydim, xdim = np.squeeze(data).shape

    if geotransform is None:
        if grid_corners is not None:
            # Determine geotransform from grid_corners
            x_ul = grid_corners['x_ul']
            y_ul = grid_corners['y_ul']
            x_lr = grid_corners['x_lr']
            y_lr = grid_corners['y_lr']

            if pixel_size is not None:
                dx = pixel_size
                dy = pixel_size
            else:
                dx = (x_lr - x_ul) / xdim
                dy = (y_lr - y_ul) / ydim

            geotransform = (
                x_ul, dx, 0.0,
                y_ul, 0.0, dy,
            )
        elif modsinu_tile is not None:
            # Determine geotransform from tile definition
            dx = MODSINU_500M_LENGTH
            dy = MODSINU_500M_LENGTH
            geotransform = get_tile_geotransform(tileID)

    srs = osr.SpatialReference()
    srs.SetFromUserInput(MODSINU_WKT_STRING)

    # Write GeoTIFF
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(
        str(fp_geotiff),
        xdim,
        ydim,
        1,
        gdal_dtype,
        options=["COMPRESS=DEFLATE"],
    )
    ds.SetGeoTransform(geotransform)
    ds.SetProjection(srs.ExportToWkt())

    geotiff_band = ds.GetRasterBand(1)
    geotiff_band.SetNoDataValue(nodata_value)
    geotiff_band.WriteArray(data)

    if color_table is not None:
        print('Color tables are not yet implemented...')

    # Close the output file
    geotiff_band.FlushCache()
    ds.FlushCache()
    ds = None  # closes and finalizes the file

    write_geotiff_report = \
        f'Wrote GEOTiff for {str(fp_geotiff)} using {geotransform}'

    return write_geotiff_report


def make_tif(meta_file: Path, input_file: Path, depth: str, output_file: Path):

    # make_tif_string = ''
    nodata = 2550
    dtype = np.uint16
    # gdal_dtype = gdal.GDT_UInt16

    if depth == "8":
        nodata = 255
        dtype = np.uint8
        # gdal_dtype = gdal.GDT_Byte

    bip_info = get_info_from_bip_file(meta_file)
    num_samples = int(bip_info["num_samples"])
    num_lines = int(bip_info["num_lines"])

    # Read raw binary grayscale data
    raw = np.frombuffer(Path(input_file).read_bytes(), dtype=dtype)
    data = raw.reshape((num_lines, num_samples))

    grid_corners = {
        'x_ul': float(bip_info["ul_corner_x"]),
        'y_ul': float(bip_info["ul_corner_y"]),
        'x_lr': float(bip_info["lr_corner_x"]),
        'y_lr': float(bip_info["lr_corner_y"]),
    }
    output_string = write_geotiff_via_gdal(
        output_file,
        data,
        geotransform=None,
        grid_corners=grid_corners,
        pixel_size=None,
        modsinu_tile=None,
        nodata_value=nodata,
        color_table=None,
    )

    return output_string


def get_tile_geotransform(tileID):
    """Return the GeoTransform string for this tileID"""
    # tileID is string of form: hHHvVV
    dx = MODSINU_500M_LENGTH
    dy = -MODSINU_500M_LENGTH

    h = int(tileID[1:3])
    v = int(tileID[4:6])

    x0 = (h - 18) * 2400 * 463.31271656938424
    y0 = (9 - v) * 2400 * 463.31271656938424

    geotransform = (x0, dx, 0.0, y0, 0.0, dy)

    return geotransform


def geotiff_from_tile_binary(ifn, ofn, tileID, xdim, ydim, dtype, nodata_val):
    """Create a geotifff from a raw binary MODIS sinusoidal grid tile"""
    data = np.fromfile(ifn, dtype=dtype).reshape(ydim, xdim)
    output_string = write_geotiff_via_gdal(
        ofn, data, modsinu_tile=tileID, nodata_value=nodata_val,
    )

    return output_string


if __name__ == '__main__':
    # Run this code at the command line from the topdir of the repo:
    #   python -m src.make_tif <input_file> <output_file> <tileID>
    #      ... <xdim> <ydim> <dtype> <nodata_val>
    #  eg
    #   python -m src.make_tif data.dat data.tif h09v05 2400 2400 uint8 255
    import sys

    try:
        ifn = sys.argv[1]
        ofn = sys.argv[2]
        tileID = sys.argv[3]
        xdim = int(sys.argv[4])
        ydim = int(sys.argv[5])
        dtype_str = sys.argv[6]
        nodata_val_str = sys.argv[7]
        if dtype_str in ('uint8', 'ubyte'):
            dtype = np.uint8
        elif dtype_str in ('uint16', 'UInt16', 'ushort'):
            dtype = np.uint16
        elif dtype_str in ('float32', 'Float32'):
            dtype = np.float32
        else:
            raise RuntimeError(f'dtype not recognized: {dtype_str}')
        try:
            nodata_val = int(nodata_val_str)
        except ValueError:
            nodata_val = float(nodata_val_str)
    except IndexError:
        print('Failed to execute make_tif() from cmdline:')
        print(f'  {sys.argv}')
        exit(1)

    print('Running make_tif() at command line:')
    print(f'  input file name: {ifn}')
    print(f' output file name: {ofn}')
    print(f'     MODIS tileID: {tileID}')
    print(f'             xdim: {xdim}')
    print(f'             ydim: {ydim}')
    print(f'            dtype: {dtype}')
    print(f'       nodata val: {nodata_val}')

    output_string = geotiff_from_tile_binary(
        ifn, ofn, tileID, xdim, ydim, dtype, nodata_val,
    )

    print(f'Finished:\n{output_string}')
