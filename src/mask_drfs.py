#!/usr/bin/env python

import configparser
import datetime as dt
import glob
import os
from pathlib import Path

import numpy as np

from src.masking import cloud16, cw_mask, h2o16
from src.constants.field_info import DTYPE_FOR_BITDEPTH, FIELD_BITDEPTHS


def get_data(filename, data_type, error_value):
    # TODO: verify with Karl that infinities should map to zeros
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


def get_bip_full_mask(working_dir, h5_root, file_info):
    bip_file = Path(working_dir) / (h5_root + file_info.get("FILE_INFO", "BIP_SUFFIX"))
    with open(bip_file, "rb") as fbip:
        data = np.fromfile(fbip, dtype=np.uint16)
    data = data.reshape(2400, 2400, 7)
    thresh_b1 = 310
    thresh_b2 = 310
    thresh_b3 = 350
    thresh_b4 = 350
    thresh_b5 = 300
    thresh_b6 = 220
    b1m = np.squeeze(data[:, :, 0]) > thresh_b1
    b2m = np.squeeze(data[:, :, 1]) > thresh_b2
    b3m = np.squeeze(data[:, :, 2]) > thresh_b3
    b4m = np.squeeze(data[:, :, 3]) > thresh_b4
    b5m = np.squeeze(data[:, :, 4]) > thresh_b5
    b6m = np.squeeze(data[:, :, 5]) > thresh_b6
    bip_full_mask = b1m & b2m & b3m & b4m & b5m & b6m
    return bip_full_mask


def cw_mask16(bfull_mask, water, data):
    results = []
    for i in np.arange(2400):
        result = map(cloud16, bfull_mask[i, :], data[i, :])
        results.append(list(result))
    data_cloud = np.array(results)
    resultsw = []
    for i in np.arange(2400):
        result = map(h2o16, water[i, :], data_cloud[i, :])
        resultsw.append(list(result))
    data_cw = np.array(resultsw)
    data_cw = data_cw.astype(np.uint16)
    return data_cw


def get_file_info_config():
    # parser = SafeConfigParser(os.environ)
    CONSTANTS_DIR = Path(__file__).parent / "constants"
    TILES_CONFIG_PATH = CONSTANTS_DIR / "file_info.ini"
    parser = configparser.ConfigParser(os.environ)
    parser.read(TILES_CONFIG_PATH)
    return parser


def get_water_mask(file_info, tile):
    water_mask_path = os.path.join(
        os.environ.get("WATER_MASK_DIR"),
        (file_info.get("FILE_INFO", "WATER_MASK_REGEX", raw=True) % tile),
    )
    water_mask_files = glob.glob(water_mask_path)
    with open(water_mask_files[0], "rb") as water_mask_file:
        water_mask_data = np.fromfile(water_mask_file, dtype=np.uint8)
    water_mask_data = water_mask_data.reshape(2400, 2400)
    return water_mask_data


def write_outfile(outfile, data_cw):
    with outfile.open("wb") as output_file:
        output_file.write(data_cw)


def mask_drfs(
    tile_id: str, date: dt.date, h5_file: Path, working_dir: Path, staging_dir: Path
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
    h5_root = h5_file.stem
    delta_vis_suffix = file_info.get("FILE_INFO", "DELTA_VIS_SUFFIX")
    delta_vis_path = Path(working_dir) / (str(h5_root) + delta_vis_suffix)
    grain_size_suffix = file_info.get("FILE_INFO", "GRAIN_SIZE_SUFFIX")
    grain_size_path = Path(working_dir) / (str(h5_root) + grain_size_suffix)
    forcing_suffix = file_info.get("FILE_INFO", "FORCING_SUFFIX")
    forcing_path = Path(working_dir) / (str(h5_root) + forcing_suffix)

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
    datestring = date.strftime("%Y%m%d")
    delta_vis_outpath = file_info.get("FILE_INFO", "DELTA_VIS_UNMASKED", raw=True) % (
        tile_id,
        datestring,
        file_info.get("FILE_INFO", "SCAGDRFS_VERSION"),
    )
    delta_vis_outfile = Path(working_dir) / delta_vis_outpath
    write_outfile(delta_vis_outfile, delta_vis_data)

    outfile_name = file_info.get("FILE_INFO", "GRAIN_SIZE_UNMASKED", raw=True) % (
        tile_id,
        datestring,
        file_info.get("FILE_INFO", "SCAGDRFS_VERSION"),
    )
    grain_size_outfile = Path(working_dir) / outfile_name
    write_outfile(grain_size_outfile, grain_data)

    forcing_name = file_info.get("FILE_INFO", "FORCING_UNMASKED", raw=True) % (
        tile_id,
        datestring,
        file_info.get("FILE_INFO", "SCAGDRFS_VERSION"),
    )
    forcing_outfile = Path(working_dir) / forcing_name
    write_outfile(forcing_outfile, forcing_data)

    bip_full_mask = get_bip_full_mask(working_dir, h5_root, file_info)

    # Apply cloud and water masks
    # TODO: Should use BITDEPTH to choose correct cw_mask[16]() routine
    delta_vis_cw = cw_mask(bip_full_mask, water_mask_data, delta_vis_data)
    grain_cw = cw_mask16(bip_full_mask, water_mask_data, grain_data)
    forcing_cw = cw_mask16(bip_full_mask, water_mask_data, forcing_data)

    # Write field output files
    datestring = date.strftime("%Y%m%d")
    delta_vis_outpath = file_info.get("FILE_INFO", "DELTA_VIS_OUTFILE", raw=True) % (
        tile_id,
        datestring,
        file_info.get("FILE_INFO", "SCAGDRFS_VERSION"),
    )
    delta_vis_outfile = Path(working_dir) / delta_vis_outpath
    write_outfile(delta_vis_outfile, delta_vis_cw)

    outfile_name = file_info.get("FILE_INFO", "GRAIN_SIZE_OUTFILE", raw=True) % (
        tile_id,
        datestring,
        file_info.get("FILE_INFO", "SCAGDRFS_VERSION"),
    )
    grain_size_outfile = Path(working_dir) / outfile_name
    write_outfile(grain_size_outfile, grain_cw)

    forcing_name = file_info.get("FILE_INFO", "FORCING_OUTFILE", raw=True) % (
        tile_id,
        datestring,
        file_info.get("FILE_INFO", "SCAGDRFS_VERSION"),
    )
    forcing_outfile = Path(working_dir) / forcing_name
    write_outfile(forcing_outfile, forcing_cw)
    return "DRFS masks completed"
