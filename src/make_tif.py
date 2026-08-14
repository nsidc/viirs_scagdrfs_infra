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
        'Wrote GEOTiff for {str(fp_geotiff)} using {geotransform}'

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
