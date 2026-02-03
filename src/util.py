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
