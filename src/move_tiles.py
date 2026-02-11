#!/usr/bin/env python

import datetime as dt
import os
import shutil
from pathlib import Path


def copy_tile_file(move_date: dt.date, input_dir: Path, output_dir: Path, tile: str):
    """Copies  tiles from the input directory specified or the
    *_NRT_DIR (environment variable) 
    """
    date_str = move_date.strftime("%Y.%m.%d")
    date_file = move_date.strftime("%Y%j")
    output_filepath = output_dir
    if output_dir == os.environ.get("WORK_DIR"):
        output_filepath = output_dir / f"{date_str}/{tile}"
    if not os.path.exists(mod09ga_output_filepath):
        os.makedirs(output_filepath)
    # TODO edit for viirs
    mod09ga_filename = f"MOD09GA.A{date_file}.{tile}"
    mod09ga_filepath_start = input_dir / f"{date_str}"
    possible_files = os.listdir(mod09ga_filepath_start)
    mod09ga_file = [f for f in possible_files if f.startswith(mod09ga_filename)]
    if (len(mod09ga_file)) < 1:
        print(f"No files match {mod09ga_filename} in {mod09ga_filepath_start}")
        return
    else:
        mod09ga_filepath = str(mod09ga_filepath_start) + "/" + mod09ga_file[0]

    shutil.copy2(mod09ga_filepath, mod09ga_output_filepath)
    print(f"{mod09ga_filename} copied to {mod09ga_output_filepath}.")

    return f"Tile files have been copied to {mod09ga_output_filepath}."
