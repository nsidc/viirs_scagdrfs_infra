#!/usr/bin/env python

import datetime as dt
import os
import shutil
from pathlib import Path


def copy_tile_file(move_date: dt.date, input_dir: Path, output_dir: Path, tile: str, product:str):
    """Copies  tiles from the input directory specified or the
    *_NRT_DIR (environment variable) 
    """
    date_str = move_date.strftime("%Y.%m.%d")
    date_file = move_date.strftime("%Y%j")
    output_filepath = output_dir
    if output_dir == os.environ.get("WORK_DIR"):
        output_filepath = output_dir / f"{product}/{date_str}/{tile}"
    if not os.path.exists(output_filepath):
        os.makedirs(output_filepath)
    # TODO edit for viirs VJ1
    # TODO: This will need to be modified for different sensors:
    #  eg:
    # MOD09GA.A2026042.h16v17.061.2026043020955.NRT.hdf
    # -----------------------
    #   filename_start (for MOD)
    # VNP09GA_NRT.A2026042.h12v02.002.2026043033539.h5
    # ---------------------------
    #     filename_start (for VNP)
    filename_start = f"{product}_NRT.A{date_file}.{tile}"
    filepath_start = input_dir / f"{date_str}"
    possible_files = os.listdir(filepath_start)
    output_file = [f for f in possible_files if f.startswith(filename_start)]
    if (len(output_file)) < 1:
        print(f"No files match {filename_start} in {filepath_start}")
        return
    else:
        filepath = str(filepath_start) + "/" + output_file[0]

    shutil.copy2(filepath, output_filepath)
    print(f"{filename_start} copied to {output_filepath}.")

    return f"Tile files have been copied to {output_filepath}."
