# type: ignore
import configparser
import datetime as dt
from ast import literal_eval
import os
import re
import logging
import glob
from pathlib import Path
from typing import Iterator

import pandas as pd

from src.contants.field_info import FIELD_BITDEPTHS, VALID_FIELD_NAMES

CONSTANTS_DIR = Path(__file__).parent / "constants"
TILES_CONFIG_PATH = CONSTANTS_DIR / "tiles.ini"


def get_list_of_defined_regions():
    config = configparser.ConfigParser()
    config.read(TILES_CONFIG_PATH)
    region_names_list = [key for key in config["TILES"].keys()]

    return region_names_list


def get_region_tile_ids(regions):
    config = configparser.ConfigParser()
    config.read(TILES_CONFIG_PATH)
    tile_ids = []
    for region in regions:
        tile_ids.extend(literal_eval(config.get("TILES", region.upper())))
    return tile_ids


def date_range(*, start_date: dt.date, end_date: dt.date) -> Iterator[dt.date]:
    """Yield a dt.date object representing each day between start_date and end_date."""
    for pd_timestamp in pd.date_range(start=start_date, end=end_date, freq="D"):
        yield pd_timestamp.date()


def get_date_from_filename(filename):
    date_regex = re.compile("\S*.A(\d{7}).\S+")
    date_matches = date_regex.search(str(filename))
    if date_matches is None:
        raise RuntimeError(f"Cannot determine date from filename: {filename}")
    file_date = dt.datetime.strptime(date_matches.group(1), "%Y%j")
    return file_date


def get_tile_id_from_filename(filename):
    tile_id_regex = re.compile("\S*(h\d{2}v\d{2})\S+")
    tile_id_matches = tile_id_regex.search(str(filename))
    if tile_id_matches is None:
        raise RuntimeError(f"Cannot determine tile ID from filename: {filename}")
    return tile_id_matches.group(1)


def check_expected_tif_files_with_glob(tif_dir, tile):
    """
    Check for expected TIF files using glob patterns with wildcards.
    """

    file_types = [
        "GS",
        "ICE",
        "ROCK",
        "SHADE",
        "SNOW",
        "VEG",
        "DELTAVIS",
        "drfsGS",
        "RF",
    ]
    expected_total = len(file_types) * 2

    # Count matching files for each type (should be 2 each - masked and unmasked)
    total_found = 0
    found_by_type = {}

    for file_type in file_types:
        # Pattern to match both masked and unmasked versions
        pattern = f"MODSCGDRF_NRT_{file_type}_{tile}_MOD09GANRT061_*_V*.tif"
        search_pattern = os.path.join(tif_dir, pattern)
        matches = glob.glob(search_pattern)
        found_by_type[file_type] = len(matches)
        total_found += len(matches)

    if total_found == expected_total:
        return True
    else:
        return False


def get_field_name(filename):
    """Return the scientific field name from a data file name
    This assumes a filename (type Path) with a .stem of the form:
    MODSCGDRF_NRT_GS_h08v04_MOD09GANRT061_20250331_V01.1.bin.mask
    ...or similar
    """
    if isinstance(filename, Path):
        base_filename = str(filename.stem)
    elif isinstance(filename, str):
        base_filename = os.path.basename(filename)
    else:
        raise RuntimeError(
            f"filename {filename} is neither Path nor str: {type(filename)}"
        )

    n_underscores = base_filename.count("_")
    if n_underscores > 3:
        fn_parts = base_filename.split("_")
        field_index = 2
    else:
        fn_parts = base_filename.split(".")
        field_index = 6

    try:
        field_name = fn_parts[field_index]
    except IndexError:
        raise RuntimeError(
            f"No index {field_index} on parts {fn_parts} for filename {filename}"
        )

    return field_name


def get_filename_stem(filename):
    """Return the base file name"""
    if isinstance(filename, str):
        base_filename = os.path.basename(os.path.splitext(filename)[0])
    elif isinstance(filename, Path):
        base_filename = filename.stem
    else:
        raise RuntimeError(f"Could not determine basename of: {filename}")

    return base_filename


def get_info_from_bip_file(meta_path):
    meta_content = None
    with meta_path.open() as meta_file:
        meta_content = meta_file.read()
    if meta_content is None:
        raise Exception(
            "Cannot read BIP metadata file: {bip_file}".format(bip_file=meta_path)
        )
    bip_meta_file = {}
    match = re.search("SOURCE_FILE=(.+)", meta_content)
    source_file = match.group(1)
    bip_meta_file["source_file"] = source_file
    match = re.search("NLINES=(\d+)", meta_content)
    nl = match.group(1)
    bip_meta_file["num_lines"] = nl
    ns = match.group(1)
    bip_meta_file["num_samples"] = ns
    match = re.search("NBANDS=(\d+)", meta_content)
    nb = match.group(1)
    bip_meta_file["num_bands"] = nb
    match = re.search("PROJ_STRING=(.+)", meta_content)
    proj_string = match.group(1)
    bip_meta_file["proj_string"] = proj_string
    match = re.search("ZONE_NUMBER=h(\d+)v(\d+)", meta_content)
    horizontal = match.group(1)
    bip_meta_file["horizontal"] = horizontal
    vertical = match.group(2)
    bip_meta_file["vertical"] = vertical
    bip_meta_file["tile_id"] = "h" + horizontal + "v" + vertical
    match = re.search("CORNER_UL_PROJECTION_X_PRODUCT=(.+)", meta_content)
    x_ul = match.group(1)
    bip_meta_file["ul_corner_x"] = x_ul
    match = re.search("CORNER_UL_PROJECTION_Y_PRODUCT=(.+)", meta_content)
    y_ul = match.group(1)
    bip_meta_file["ul_corner_y"] = y_ul
    match = re.search("CORNER_LR_PROJECTION_X_PRODUCT=(.+)", meta_content)
    x_lr = match.group(1)
    bip_meta_file["lr_corner_x"] = x_lr
    match = re.search("CORNER_LR_PROJECTION_Y_PRODUCT=(.+)", meta_content)
    y_lr = match.group(1)
    bip_meta_file["lr_corner_y"] = y_lr
    return bip_meta_file
