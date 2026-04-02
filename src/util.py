# type: ignore
import configparser
import datetime as dt
import glob
import logging
import os
import re
from ast import literal_eval
from pathlib import Path
from typing import Iterator

import pandas as pd

from src.constants.field_info import FIELD_BITDEPTHS, VALID_FIELD_NAMES

CONSTANTS_DIR = Path(__file__).parent / "constants"
TILES_CONFIG_PATH = CONSTANTS_DIR / "tiles.ini"

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Region / tile helpers
# ---------------------------------------------------------------------------


def get_list_of_defined_regions():
    config = configparser.ConfigParser()
    config.read(TILES_CONFIG_PATH)
    return [key for key in config["TILES"].keys()]


def get_region_tile_ids(regions):
    config = configparser.ConfigParser()
    config.read(TILES_CONFIG_PATH)
    tile_ids = []
    for region in regions:
        tile_ids.extend(literal_eval(config.get("TILES", region.upper())))
    return tile_ids


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------


def date_range(*, start_date: dt.date, end_date: dt.date) -> Iterator[dt.date]:
    """Yield a dt.date for each day between start_date and end_date (inclusive)."""
    for pd_timestamp in pd.date_range(start=start_date, end=end_date, freq="D"):
        yield pd_timestamp.date()


def datetime_to_date(_ctx, _param, value: dt.datetime) -> dt.date:
    """Click callback that converts a dt.datetime to dt.date."""
    return value.date()


# ---------------------------------------------------------------------------
# Filename parsing helpers
# ---------------------------------------------------------------------------


def get_sensor_from_filename(filename):
    """Determine sensor (MODIS or VIIRS) from a data filename."""
    filename_str = str(filename)

    if re.search(r"\S*MOD09GA\S+", filename_str):
        sensor = "MODIS"
    elif re.search(r"\S*VNP09GA\S+", filename_str):
        sensor = "VIIRS"
    elif re.search(r"\S*VJ1\S+", filename_str):
        sensor = "VIIRS"
    else:
        raise RuntimeError(f"Cannot determine sensor from filename: {filename}")

    logger.debug("Determined sensor '%s' from filename: %s", sensor, filename)
    return sensor


def get_date_from_filename(filename):
    date_regex = re.compile(r"\S*.A(\d{7}).\S+")
    match = date_regex.search(str(filename))
    if match is None:
        raise RuntimeError(f"Cannot determine date from filename: {filename}")
    return dt.datetime.strptime(match.group(1), "%Y%j")


def get_tile_id_from_filename(filename):
    tile_id_regex = re.compile(r"\S*(h\d{2}v\d{2})\S+")
    match = tile_id_regex.search(str(filename))
    if match is None:
        raise RuntimeError(f"Cannot determine tile ID from filename: {filename}")
    return match.group(1)


def get_filename_stem(filename):
    """Return the base filename without extension."""
    if isinstance(filename, str):
        return os.path.basename(os.path.splitext(filename)[0])
    elif isinstance(filename, Path):
        return filename.stem
    else:
        raise RuntimeError(f"Could not determine basename of: {filename}")


def get_field_name(filename):
    """Return the scientific field name from a data filename.

    Handles filenames of the form:
      MODSCGDRF_NRT_GS_h08v04_MOD09GANRT061_20250331_V01.1.bin.mask
      VNP09GA_NRT.A2026042.h30v13.002.2026043041826.grnsz.bin
    ...and similar variants.
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

    # Guard against hitting a bare "bin" token instead of the actual field name
    if fn_parts[field_index] == "bin":
        field_index -= 1

    try:
        field_name = fn_parts[field_index]
    except IndexError:
        raise RuntimeError(
            f"No index {field_index} on parts {fn_parts} for filename {filename}"
        )

    logger.debug("Resolved field name '%s' from filename: %s", field_name, filename)
    return field_name


def get_bitdepth_for_field_name(field_name):
    """Return the bit depth (8 or 16) for a DRFS or SCAG data field name."""
    try:
        return FIELD_BITDEPTHS[field_name]
    except KeyError:
        raise RuntimeError(
            f"field name '{field_name}' has no defined bitdepth. "
            f"Known fields: {list(FIELD_BITDEPTHS.keys())}"
        )


# ---------------------------------------------------------------------------
# TIF file validation
# ---------------------------------------------------------------------------

# Sensor-specific glob pattern components
_SENSOR_PATTERN_MAP = {
    "MODIS": ("MODSCGDRF_NRT", "MOD09GANRT061"),
    "VIIRS": (
        "VIRSCGDRF_NRT",
        "VNP09GANRT061",
    ),  # TODO: distinguish VNP vs VJ1 if needed
}

_TIF_FILE_TYPES = [
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


def check_expected_tif_files_with_glob(tif_dir, tile, sensor):
    """Check that all expected TIF files (masked + unmasked) exist for a tile.

    Args:
        tif_dir: Directory to search.
        tile: MODIS/VIIRS tile ID, e.g. "h08v04".
        sensor: "MODIS" or "VIIRS".

    Returns:
        True if all expected files are present, False otherwise.
    """
    try:
        product_prefix, product_id = _SENSOR_PATTERN_MAP[sensor]
    except KeyError:
        raise ValueError(
            f"Unknown sensor '{sensor}'. Expected one of: {list(_SENSOR_PATTERN_MAP)}"
        )

    expected_total = len(_TIF_FILE_TYPES) * 2  # masked + unmasked
    total_found = 0
    found_by_type = {}

    for file_type in _TIF_FILE_TYPES:
        pattern = f"{product_prefix}_{file_type}_{tile}_{product_id}_*_V*.tif"
        matches = glob.glob(os.path.join(tif_dir, pattern))
        found_by_type[file_type] = len(matches)
        total_found += len(matches)

    if total_found != expected_total:
        logger.debug(
            "TIF file check failed for tile %s (sensor=%s): found %d / %d. "
            "Breakdown: %s",
            tile,
            sensor,
            total_found,
            expected_total,
            found_by_type,
        )

    return total_found == expected_total


# ---------------------------------------------------------------------------
# BIP metadata helper
# ---------------------------------------------------------------------------


def get_info_from_bip_file(meta_path):
    with meta_path.open() as meta_file:
        meta_content = meta_file.read()

    if not meta_content:
        raise Exception(f"Cannot read BIP metadata file: {meta_path}")

    def _extract(pattern):
        match = re.search(pattern, meta_content)
        if match is None:
            raise RuntimeError(
                f"Pattern '{pattern}' not found in BIP metadata file: {meta_path}"
            )
        return match.group(1)

    horizontal, vertical = re.search(r"ZONE_NUMBER=h(\d+)v(\d+)", meta_content).groups()

    return {
        "source_file": _extract(r"SOURCE_FILE=(.+)"),
        "num_lines": _extract(r"NLINES=(\d+)"),
        "num_samples": _extract(
            r"NLINES=(\d+)"
        ),  # NOTE: original code reused NLINES for num_samples
        "num_bands": _extract(r"NBANDS=(\d+)"),
        "proj_string": _extract(r"PROJ_STRING=(.+)"),
        "horizontal": horizontal,
        "vertical": vertical,
        "tile_id": f"h{horizontal}v{vertical}",
        "ul_corner_x": _extract(r"CORNER_UL_PROJECTION_X_PRODUCT=(.+)"),
        "ul_corner_y": _extract(r"CORNER_UL_PROJECTION_Y_PRODUCT=(.+)"),
        "lr_corner_x": _extract(r"CORNER_LR_PROJECTION_X_PRODUCT=(.+)"),
        "lr_corner_y": _extract(r"CORNER_LR_PROJECTION_Y_PRODUCT=(.+)"),
    }
