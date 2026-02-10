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
