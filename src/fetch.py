#!/usr/bin/env python

import os
from pathlib import Path

import earthaccess
from filelock import SoftFileLock, Timeout

from src.util import (
    get_region_tile_ids,
    get_list_of_defined_regions,
    get_tile_id_from_filename,
)
from src.constants import (
    PRODUCT_SHORT_NAME,
    PRODUCT_CONCEPT_ID,
    LOCK_TIMEOUT,
    TARGET_GROUP_ID,
    FILE_PERMISSIONS,
    DIR_PERMISSIONS,
)


ALL_REGIONS = get_list_of_defined_regions()
TILES = get_region_tile_ids(ALL_REGIONS)
TILES_SET = set(TILES)  # Convert to set for faster lookup


def get_data(date, concept_id, dated_output_dir):
    """
    Download VIIRS VJ109GA data for specified date and region tiles.

    Args:
        date: datetime object for the date to download
        concept_id: NASA Earthdata concept ID for VJ109GA dataset
        dated_output_dir: Path object or string for output directory

    Returns:
        list: Downloaded file paths, or empty list on failure
    """
    lockfile_path = Path(dated_output_dir / "file.lock")
    try:
        lockfile = SoftFileLock(str(lockfile_path), timeout=10)
        with lockfile:
            print("logging into earthdata...")
            earthaccess.login()

            print(f"Searching for {PRODUCT_SHORT_NAME} data...")
            results = earthaccess.search_data(
                short_name=PRODUCT_SHORT_NAME,
                concept_id=concept_id,
                temporal=(date.strftime("%Y-%m-%d"), date.strftime("%Y-%m-%d")),
            )

            print("Found ", len(results), " granules.")
            filtered_results = []
            skipped_no_links = 0
            skipped_no_match = 0
            for result in results:
                data_link = result.data_links()
                if not data_link:
                    skipped_no_links += 1
                    continue

                filename = data_link[0].split("/")[-1]
                tile_id = get_tile_id_from_filename(filename)

                if tile_id in TILES_SET:
                    filtered_results.append(result)
                else:
                    skipped_no_match += 1

            print(f"Skipped (no data links): {skipped_no_links}")
            print(f"Skipped (tile not in set): {skipped_no_match}")
            print(
                f"Filtered to {len(filtered_results)} granules matching region tiles."
            )
            if not filtered_results:
                print("No matching granules found for download.")
                return []

            print(
                f"Filtered to {len(filtered_results)} granules matching our tiles to download."
            )
            print("Downloading data to ", dated_output_dir)
            try:
                files = earthaccess.download(filtered_results, dated_output_dir)
            except Exception as e:
                print(f"WARNING: some downloads failed with error: {type(e).__name__}")
                files = list(dated_output_dir.glob("*.h5"))

            print("Downloaded ", len(files), " files to ", dated_output_dir)

            return files

    except Timeout:
        print(
            "Was not able to get file lock", str(lockfile_path), "within timeout limit."
        )
        print("If the directory is free, please remove the lock file and try again.")


def chmod_data(dated_output_dir):
    try:
        dated_output_dir.chmod(FILE_PERMISSIONS)
        for file in dated_output_dir.rglob("*"):
            file.chmod(FILE_PERMISSIONS)
    except PermissionError:
        print(
            "The directory and/or files in the directory ",
            dated_output_dir,
            " are not owned and permissions cannot be defined.",
        )


def chown_data(dated_output_dir):
    """Change group to dscottgrp so everyone has access."""
    try:
        os.chown(dated_output_dir, -1, TARGET_GROUP_ID)
        for file in dated_output_dir.rglob("*"):
            os.chown(file, -1, TARGET_GROUP_ID)
    except (PermissionError, OSError) as e:
        print(
            f"Could not change group ownership on {dated_output_dir}: {e}",
        )
