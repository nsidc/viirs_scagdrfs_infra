#!/usr/bin/env python
"""Fetch VIIRS NRT data for SCAGDRFS regions."""

import os
from pathlib import Path

try:
    import earthaccess
    from filelock import SoftFileLock, Timeout
except ModuleNotFoundError as e:
    print(
        f"ERROR: {e}\n"
        "Make sure you're running in the 'viirs' conda environment:\n"
        "  conda activate viirs"
    )
    sys.exit(1)

from src.util import (
    get_region_tile_ids,
    get_list_of_defined_regions,
    get_tile_id_from_filename,
)
from src.constants import (
    LOCK_TIMEOUT,
    TARGET_GROUP_ID,
    FILE_PERMISSIONS,
)

ALL_REGIONS = get_list_of_defined_regions()
TILES = get_region_tile_ids(ALL_REGIONS)
TILES_SET = set(TILES)


def get_data(date, concept_id, dated_output_dir, short_name):
    """
    Download VIIRS data for specified date and region tiles.

    Args:
        date: datetime object for the date to download
        concept_id: NASA Earthdata concept ID for dataset
        dated_output_dir: Path object or string for output directory
        short_name: Product short name (e.g. VJ109GA_NRT or VNP09GA_NRT)

    Returns:
        list: Downloaded file paths, or empty list on failure
    """
    dated_output_dir = Path(dated_output_dir)
    dated_output_dir.mkdir(parents=True, exist_ok=True)

    lockfile_path = dated_output_dir / "file.lock"
    try:
        lockfile = SoftFileLock(str(lockfile_path), timeout=LOCK_TIMEOUT)
        with lockfile:
            print("logging into earthdata...")
            earthaccess.login()

            print(f"Searching for {short_name} data...")
            results = earthaccess.search_data(
                concept_id=concept_id,
                temporal=(date.strftime("%Y-%m-%d"), date.strftime("%Y-%m-%d")),
            )

            print(f"Found {len(results)} granules.")
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

            print(f"Downloading data to {dated_output_dir}")
            try:
                files = earthaccess.download(filtered_results, dated_output_dir)
            except Exception as e:
                print(f"WARNING: some downloads failed with error: {type(e).__name__}")
                files = list(dated_output_dir.glob("*.h5")) + list(
                    dated_output_dir.glob("*.hdf")
                )

            print(f"Downloaded {len(files)} files to {dated_output_dir}")
            return files

    except Timeout:
        print(
            f"ERROR: Could not acquire lock on {lockfile_path} within {LOCK_TIMEOUT} seconds."
        )
        print("If the directory is free, please remove the lock file and try again.")
        return []
    except PermissionError:
        print(
            f"INFO: Cannot write lock file to {dated_output_dir} — "
            "data for this date was likely already downloaded by another user. Skipping."
        )
        return []


def chmod_data(dated_output_dir):
    """Set permissions to 775 for directory and all contents."""
    dated_output_dir = Path(dated_output_dir)

    if not dated_output_dir.exists():
        print(f"WARNING: Directory {dated_output_dir} does not exist.")
        return

    try:
        dated_output_dir.chmod(FILE_PERMISSIONS)
        for file_path in dated_output_dir.rglob("*"):
            file_path.chmod(FILE_PERMISSIONS)
    except PermissionError as e:
        print(
            f"WARNING: Permission denied when setting permissions on {dated_output_dir}: {e}"
        )


def chown_data(dated_output_dir):
    """Change group ownership to dscottgrp for shared access."""
    dated_output_dir = Path(dated_output_dir)

    if not dated_output_dir.exists():
        print(f"WARNING: Directory {dated_output_dir} does not exist.")
        return

    try:
        os.chown(dated_output_dir, -1, TARGET_GROUP_ID)
        for file_path in dated_output_dir.rglob("*"):
            os.chown(file_path, -1, TARGET_GROUP_ID)
    except (PermissionError, OSError) as e:
        print(f"WARNING: Could not change group ownership on {dated_output_dir}: {e}")
