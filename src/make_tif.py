import numpy as np
from pathlib import Path
from osgeo import gdal, osr

from src.util import (
    get_info_from_bip_file,
)


def make_tif(meta_file: Path, input_file: Path, depth: str, output_file: Path):

    make_tif_string = ''
    nodata = 2550
    dtype = np.uint16
    gdal_dtype = gdal.GDT_UInt16

    if depth == "8":
        nodata = 255
        dtype = np.uint8
        gdal_dtype = gdal.GDT_Byte

    bip_info = get_info_from_bip_file(meta_file)
    num_samples = int(bip_info["num_samples"])
    num_lines = int(bip_info["num_lines"])

    # Read raw binary grayscale data
    raw = np.frombuffer(Path(input_file).read_bytes(), dtype=dtype)
    data = raw.reshape((num_lines, num_samples))

    # Compute geotransform from corner coordinates
    # TODO: These values are derived from the tileID.
    #       We should pull directly from lookup using tileID as index,
    #       rather than indirectly relying on the .bip.meta file.
    ul_x = float(bip_info["ul_corner_x"])
    ul_y = float(bip_info["ul_corner_y"])
    lr_x = float(bip_info["lr_corner_x"])
    lr_y = float(bip_info["lr_corner_y"])
    pixel_width = (lr_x - ul_x) / num_samples
    pixel_height = (lr_y - ul_y) / num_lines  # negative: y decreases top→bottom

    geotransform = (ul_x, pixel_width, 0.0, ul_y, 0.0, pixel_height)

    # Parse the projection string into an OGC WKT SRS
    srs = osr.SpatialReference()

    # FIXME: The bip_info["proj_string"] is yielding a bizarre string,
    #        so am hardcoding the MODIS sinusoidal projection here.
    #   The bip_info string value is:
    #     bip_info["proj_string"]=\\\'"+proj=sinu +R=6371007.181 +nadgrids=@null +wktext"\\\'
    #   The hardcoded replacement value here is:
    #     "+proj=sinu +R=6371007.181"
    #   Note: this removes the obsolete 'nagrids' and 'wktext' flags
    #         and sets the Earth radius to the value that *exactly* matches
    #         MOD09GA in-file georeferencing.

    # Attempting to use WKT instead of proj-string because proj-string does not
    #   explicitly specify a datum.
    # modis_sinu_proj_string = "+proj=sinu +R=6371007.181"
    # srs.SetFromUserInput(modis_sinu_proj_string)  # accepts PROJ4, EPSG:, WKT, etc.

    # With this, we get an error because "inf" is not a double-precision number
    # modis_sinu_WKT_string = 'PROJCS["Sinusoidal",GEOGCS["GCS_Unknown",DATUM["D_unknown",SPHEROID["Unknown",6371007.181,"inf"]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]],PROJECTION["Sinusoidal"],PARAMETER["central_meridian",0],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["Meter",1]]'
    modis_sinu_WKT_string = 'PROJCS["Sinusoidal",GEOGCS["GCS_Unknown",DATUM["D_unknown",SPHEROID["Unknown",6371007.181,0]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]],PROJECTION["Sinusoidal"],PARAMETER["central_meridian",0],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["Meter",1]]'
    srs.SetFromUserInput(modis_sinu_WKT_string)  # accepts PROJ4, EPSG:, WKT, etc.

    # Write GeoTIFF with DEFLATE compression
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(
        str(output_file),
        num_samples,
        num_lines,
        1,  # 1 band
        gdal_dtype,
        options=["COMPRESS=DEFLATE"],
    )
    ds.SetGeoTransform(geotransform)
    ds.SetProjection(srs.ExportToWkt())

    band = ds.GetRasterBand(1)
    band.SetNoDataValue(nodata)
    band.WriteArray(data)

    # TODO: This would be a good place to add colormap / colortable information to the geotiffs

    band.FlushCache()
    ds.FlushCache()
    ds = None  # closes and finalizes the file

    return make_tif_string
