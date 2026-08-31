#!/usr/bin/env python

import configparser
import datetime as dt
import glob
import os
import shutil
from ast import literal_eval
from pathlib import Path

from scagdrfs_infra.util import date_range, get_region_tile_ids

config = configparser.ConfigParser()
config.read(f"{os.environ.get('SCAGDRFS_CONSTANTS_DIR')}/parameters.ini")
params = literal_eval(config["PARAMETERS"]["params"])


# Note regions may be list here
def copy_output_to_peta(
    start_date: dt.date,
    end_date: dt.date,
    input_dir: Path,
    output_dir: Path,
    regions: str,
    product: str,
):
    """
    Copies scag and drfs output files to the PETA library.
    """
    for date in date_range(start_date=start_date, end_date=end_date):
        date_str = date.strftime("%Y%m%d")
        tile_ids = get_region_tile_ids(regions)

        missing_filepath = os.path.join(
            output_dir, date.strftime("%Y.%m.%d"), "missing_files.txt"
        )
        if os.path.exists(missing_filepath):
            os.remove(missing_filepath)
            print(f"Removed existing file: {missing_filepath}")

        for tile in tile_ids:
            date_folder = date.strftime("%Y.%m.%d")
            base_path = os.path.join(input_dir, date_folder, tile)
            nc_pattern = os.path.join(base_path, "*.nc")
            hdf_file = glob.glob(os.path.join(base_path, "*.hdf"))

            output_path = os.path.join(output_dir, date_folder, tile)
            os.makedirs(output_path, exist_ok=True)

            # if no HDF file exists move empty netcdf
            if not hdf_file:
                print(f"There is no hdf file in {base_path}")
                # Process NC files
                nc_files = glob.glob(nc_pattern)

                for nc_filepath in nc_files:
                    shutil.copy2(
                        nc_filepath,
                        os.path.join(output_path, os.path.basename(nc_filepath)),
                    )
            else:
                for param in params:
                    # Define paths and patterns

                    tif_pattern = f"MODSCGDRF_NRT_{param}_{tile}_MOD09GANRT061_{date_str}_V01.*.tif"

                    # Process TIF files (masked and unmasked)
                    full_pattern = os.path.join(base_path, tif_pattern)
                    matching_files = glob.glob(full_pattern)

                    for filepath in matching_files:
                        shutil.copy2(
                            filepath,
                            os.path.join(output_path, os.path.basename(filepath)),
                        )

                    if not matching_files:
                        missing_filepath = os.path.join(
                            input_dir, date_folder, "missing_files.txt"
                        )
                        os.makedirs(os.path.dirname(missing_filepath), exist_ok=True)
                        with open(missing_filepath, "a+") as file:
                            file.write(f"Missing file for pattern: {full_pattern}. \n")

                    # Process NC files
                    nc_files = glob.glob(nc_pattern)

                    for nc_filepath in nc_files:
                        shutil.copy2(
                            nc_filepath,
                            os.path.join(output_path, os.path.basename(nc_filepath)),
                        )

                    if not nc_files:
                        missing_filepath = os.path.join(
                            input_dir, date_folder, "missing_files.txt"
                        )
                        os.makedirs(os.path.dirname(missing_filepath), exist_ok=True)
                        with open(missing_filepath, "a+") as file:
                            file.write(
                                f"Missing NetCDF file for {tile} on {date_str}.\n"
                            )
        return None
