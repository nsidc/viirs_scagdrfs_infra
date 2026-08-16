import configparser
import datetime as dt
# import glob
import os
from pathlib import Path
import logging

import numpy as np

from src.masking import cw_mask
from src.constants.field_info import DTYPE_FOR_BITDEPTH, FIELD_BITDEPTHS
from src.constants.paths import DRFS_COMPONENT_DIR
from src.constants.products import PRODUCT_OUTPUT_PREFIX, PRODUCT_SOURCE_ID
from src.drfs_components import read_geotiff

logger = logging.getLogger(__name__)

def get_data(filename, data_type, error_value):
    with filename.open("rb") as data_file:
        data = np.fromfile(data_file, dtype=np.float32)
    data = data.reshape(2400, 2400)
    data[data < 0.0] = error_value
    data[data > error_value] = error_value
    infinity_value = 0
    no_nan_data = np.nan_to_num(
        data, nan=infinity_value, posinf=infinity_value, neginf=infinity_value
    )
    data = no_nan_data.astype(data_type)

    return data


def get_cloud_mask_6band(working_dir, src_root, file_info):
    bip_file = Path(working_dir) / (src_root + file_info.get("FILE_INFO", "BIP_SUFFIX"))
    with open(bip_file, "rb") as fbip:
        data = np.fromfile(fbip, dtype=np.int16)
    try:
        data = data.reshape(2400, 2400, 7)
    except ValueError as e:
        print("Error attempting to reshape data")
        print(f"  bip_file: {bip_file}")
        print(f"  size of bip_files data: {data.size}")
        raise e

    # Band label for (M)ODIS or (V)IIRS in comment string
    thresh_b1 = 310  # M: b03  V: M3
    thresh_b2 = 310  # M: b04  V: M4
    thresh_b3 = 350  # M: b01  V: M5
    thresh_b4 = 350  # M: b02  V: I2
    thresh_b5 = 300  # M: b05  V: M8
    thresh_b6 = 220  # M: b06  V: I3
    b1m = np.squeeze(data[:, :, 0]) > thresh_b1
    b2m = np.squeeze(data[:, :, 1]) > thresh_b2
    b3m = np.squeeze(data[:, :, 2]) > thresh_b3
    b4m = np.squeeze(data[:, :, 3]) > thresh_b4
    b5m = np.squeeze(data[:, :, 4]) > thresh_b5
    b6m = np.squeeze(data[:, :, 5]) > thresh_b6
    cloud_mask_6band = b1m & b2m & b3m & b4m & b5m & b6m
    return cloud_mask_6band


def get_file_info_config():
    CONSTANTS_DIR = Path(__file__).parent / "constants"
    TILES_CONFIG_PATH = CONSTANTS_DIR / "file_info.ini"
    parser = configparser.ConfigParser(os.environ)
    parser.read(TILES_CONFIG_PATH)
    return parser


def get_water_mask(file_info, tile):
    """Return water mask where tile is 100% covered by water"""

    # The '*' in '...*.tif' is for a version string in the file name:
    #   eg: waterpercentage_h07v03_v0.tif
    waterpercentage_files = \
        list((DRFS_COMPONENT_DIR / "waterpercentage").glob(f'waterpercentage_{tile}*.tif'))
    if len(waterpercentage_files) != 1:
        raise RuntimeError(
            f"Expected 1 waterpercentage file for {tile}, found {len(waterpercentage_files)}:"
            f"{waterpercentage_files}"
        )
    waterpercentage_file = waterpercentage_files[0]
    waterpercentage = read_geotiff(waterpercentage_file)
    logger.debug(
        f"Loaded waterpercentage for {tile} from: {waterpercentage_file}"
    )
    return waterpercentage


def write_outfile(outfile, data_cw):
    with outfile.open("wb") as output_file:
        output_file.write(data_cw)


def mask_drfs(
    tile_id: str,
    date: dt.date,
    src_file: Path,
    working_dir: Path,
    staging_dir: Path,
    product: str,
):
    # Add suffix to default working and staging dirs.
    if str(working_dir) == os.environ.get("WORK_DIR"):
        working_dir = working_dir / date.strftime("%Y.%m.%d") / tile_id
    # Tifs do not write out properly to staging dir. Why?
    if str(staging_dir) == os.environ.get("STAGING_DIR"):
        staging_dir = staging_dir / date.strftime("%Y.%m.%d") / tile_id

    file_info = get_file_info_config()
    water_mask_data = get_water_mask(file_info, tile_id)

    # Created .dat file names from IDL processing
    src_root = src_file.stem
    delta_vis_suffix = file_info.get("FILE_INFO", "DELTA_VIS_SUFFIX")
    delta_vis_path = Path(working_dir) / (str(src_root) + delta_vis_suffix)
    grain_size_suffix = file_info.get("FILE_INFO", "GRAIN_SIZE_SUFFIX")
    grain_size_path = Path(working_dir) / (str(src_root) + grain_size_suffix)
    forcing_suffix = file_info.get("FILE_INFO", "FORCING_SUFFIX")
    forcing_path = Path(working_dir) / (str(src_root) + forcing_suffix)

    # Get binary data and change error values
    delta_vis_data = get_data(
        delta_vis_path, DTYPE_FOR_BITDEPTH[FIELD_BITDEPTHS["DELTAVIS"]], 255
    )
    grain_data = get_data(
        grain_size_path, DTYPE_FOR_BITDEPTH[FIELD_BITDEPTHS["drfsGS"]], 2550
    )
    forcing_data = get_data(
        forcing_path, DTYPE_FOR_BITDEPTH[FIELD_BITDEPTHS["RF"]], 2550
    )

    delta_vis_data[grain_data <= 0.0] = 255
    forcing_data[grain_data <= 0.0] = 2550
    grain_data[grain_data == 0.0] = 2550

    # Write unmasked field output files
    prefix = PRODUCT_OUTPUT_PREFIX[product.upper()]
    source_id = PRODUCT_SOURCE_ID[product.upper()]
    datestring = date.strftime("%Y%m%d")
    delta_vis_outpath = file_info.get("FILE_INFO", "DELTA_VIS_UNMASKED", raw=True) % (
        prefix,
        tile_id,
        source_id,
        datestring,
        file_info.get("FILE_INFO", "SCAGDRFS_VERSION"),
    )
    delta_vis_outfile = Path(working_dir) / delta_vis_outpath
    write_outfile(delta_vis_outfile, delta_vis_data)

    outfile_name = file_info.get("FILE_INFO", "GRAIN_SIZE_UNMASKED", raw=True) % (
        prefix,
        tile_id,
        source_id,
        datestring,
        file_info.get("FILE_INFO", "SCAGDRFS_VERSION"),
    )
    grain_size_outfile = Path(working_dir) / outfile_name
    write_outfile(grain_size_outfile, grain_data)

    forcing_name = file_info.get("FILE_INFO", "FORCING_UNMASKED", raw=True) % (
        prefix,
        tile_id,
        source_id,
        datestring,
        file_info.get("FILE_INFO", "SCAGDRFS_VERSION"),
    )
    forcing_outfile = Path(working_dir) / forcing_name
    write_outfile(forcing_outfile, forcing_data)

    cloud_mask_6band = get_cloud_mask_6band(working_dir, src_root, file_info)

    # Apply cloud and water masks
    delta_vis_cw = cw_mask(cloud_mask_6band, water_mask_data, delta_vis_data)
    grain_cw = cw_mask(cloud_mask_6band, water_mask_data, grain_data)
    forcing_cw = cw_mask(cloud_mask_6band, water_mask_data, forcing_data)

    # Write field output files
    datestring = date.strftime("%Y%m%d")
    delta_vis_outpath = file_info.get("FILE_INFO", "DELTA_VIS_OUTFILE", raw=True) % (
        prefix,
        tile_id,
        source_id,
        datestring,
        file_info.get("FILE_INFO", "SCAGDRFS_VERSION"),
    )
    delta_vis_outfile = Path(working_dir) / delta_vis_outpath
    write_outfile(delta_vis_outfile, delta_vis_cw)

    outfile_name = file_info.get("FILE_INFO", "GRAIN_SIZE_OUTFILE", raw=True) % (
        prefix,
        tile_id,
        source_id,
        datestring,
        file_info.get("FILE_INFO", "SCAGDRFS_VERSION"),
    )
    grain_size_outfile = Path(working_dir) / outfile_name
    write_outfile(grain_size_outfile, grain_cw)

    forcing_name = file_info.get("FILE_INFO", "FORCING_OUTFILE", raw=True) % (
        prefix,
        tile_id,
        source_id,
        datestring,
        file_info.get("FILE_INFO", "SCAGDRFS_VERSION"),
    )
    forcing_outfile = Path(working_dir) / forcing_name
    write_outfile(forcing_outfile, forcing_cw)

    return "DRFS masks completed"
