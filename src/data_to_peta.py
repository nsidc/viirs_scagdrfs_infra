#!/usr/bin/env python

import datetime as dt
import glob
import os
import shutil
from pathlib import Path

from src.util import date_range
from src.constants.paths import WORK_DIR


# Note regions may be list here
def copy_output_to_peta(
    start_date: dt.date,
    end_date: dt.date,
    input_dir: Path,
):
    """
    Copies scag and drfs output files to daac data transfer area
    """
    for date in date_range(start_date=start_date, end_date=end_date):
        date_folder = date.strftime("%Y.%m.%d")
        base_path = os.path.join(input_dir, date_folder)

        output_dir = "/pl/active/DAAC-data-transfer/metgenc/vj1scgdrf_nrt/data"  # output dir for flattened files

        # Find and copy only .nc files (removes tile structure)
        for root, _, files in os.walk(base_path):
            for file in files:
                if file.endswith(".nc"):
                    source_file = os.path.join(root, file)
                    destination_file = os.path.join(output_dir, file)  # Flatten files
                    print(f"{file} being copied to {destination_file}")
                    shutil.copy2(source_file, destination_file)  # Preserve metadata

        return None
