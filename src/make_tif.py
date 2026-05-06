#!/usr/bin/env python

import os
import subprocess
from pathlib import Path

from src.constants.paths import WORK_DIR
from src.util import (
    get_date_from_filename,
    get_filename_stem,
    get_info_from_bip_file,
)


def make_tif(meta_file: Path, input_file: Path, depth: str, output_file: Path):
    nodata = 2550
    if depth == "8":
        nodata = 255

    bip_info = get_info_from_bip_file(meta_file)

    # TODO: Create unique temp files
    temp_file_basename = get_filename_stem(input_file)
    temp_file = os.path.join(
        WORK_DIR,
        get_date_from_filename(bip_info["source_file"]).strftime("%Y.%m.%d"),
        bip_info["tile_id"],
        f"{temp_file_basename}.temptif",
    )

    # TODO: convert can use tif:<filename> to force an image format
    cmd = (
        f"convert -size {bip_info['num_samples']}x{bip_info['num_lines']} -depth {depth} "
        f"-define quantum:format=unsigned gray:{input_file} tif:{temp_file}"
    )
    print("Running: ", cmd)
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, executable="/usr/bin/bash"
    )
    print("result: ", result.stdout)
    result.check_returncode()

    cmd = (
        f"gdal_translate -a_nodata {nodata} -a_srs {bip_info['proj_string']} "
        f"-a_ullr {bip_info['ul_corner_x']} {bip_info['ul_corner_y']} {bip_info['lr_corner_x']}"
        f" {bip_info['lr_corner_y']} -co COMPRESS=DEFLATE -if GTiff {temp_file} {output_file}"
    )
    print("Running: ", cmd)
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, executable="/usr/bin/bash"
    )
    print("result: ", result.stdout)
    result.check_returncode()

    os.remove(temp_file)
