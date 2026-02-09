#!/usr/bin/env python
"""Fetch VIIRS VJ109GA Near Real-Time (NRT) data from NASA LANCE."""

import datetime as dt
from pathlib import Path
import logging
import stat

import click

from src.fetch import chmod_data, chown_data, get_data
from src.util import date_range
from src.constants import VJ109GA_NRT_DIR, FILE_PERMISSIONS

# LANCE MODIS concept ID for VJ109GA NRT
# Source: https://search.earthdata.nasa.gov/search/granules?p=C2781246545-LANCEMODIS
LANCE_CONCEPT_ID = "C2781246545-LANCEMODIS"

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def move_granules_to_date_dirs(dated_output_dir, base_output_dir):
    """
    Ensure files are in the correct date directory based on their DOY.

    VIIRS filenames contain a DOY (day of year) that may not match the folder
    they were downloaded to. This function moves files to their correct date folder.

    Args:
        dated_output_dir: Path to the directory being checked
        base_output_dir: Path to the base output directory for all dates
    """
    try:
        folder_doy = dt.datetime.strptime(dated_output_dir.name, "%Y.%m.%d").strftime(
            "%Y%j"
        )
    except ValueError:
        logging.warning(f"Skipping non-date folder: {dated_output_dir}")
        return

    for f in list(dated_output_dir.glob("*.h5")) + list(dated_output_dir.glob("*.hdf")):
        parts = f.name.split(".")
        if len(parts) < 3:
            continue  # skip malformed filenames

        # Extract DOY from filename
        file_doy = parts[1][1:]  # e.g., 'A2024142' -> '2024142'

        if file_doy != folder_doy:
            # Move to the correct folder
            try:
                correct_date = dt.datetime.strptime(file_doy, "%Y%j").strftime(
                    "%Y.%m.%d"
                )
            except ValueError:
                logging.warning(
                    f"Warning: could not parse DOY from filename '{f.name}'"
                )
                continue  # skip this file, it's not a valid MODIS filename

            correct_folder = base_output_dir / correct_date
            correct_folder.mkdir(parents=True, exist_ok=True)
            dest = correct_folder / f.name

            if dest.exists():
                new_size = f.stat().st_size
                existing_size = dest.stat().st_size

                # skip zero-byte files
                if new_size == 0 and existing_size != 0:  # Fixed: changed & to and
                    logger.info(f"Warning skipping 0-byte file: {f.name}")
                    f.unlink()
                    continue

                # replace if newer
                if f.stat().st_mtime > dest.stat().st_mtime:
                    logger.info(
                        f"Replacing outdated file in {correct_folder}: {dest.name}"
                    )
                    dest.unlink()
                    f.rename(dest)
                    dest.chmod(
                        stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH
                    )
                else:
                    logger.info(f"File already exists and is up to date: {dest.name}")
                    f.unlink()
            else:
                # move to correct folder
                logger.info(f"Moving {f.name} -> {correct_folder}")
                f.rename(dest)
                dest.chmod(stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)


@click.command()
@click.option(
    "-s",
    "--start-date",
    type=click.DateTime(formats=["%Y%m%d", "%Y-%m-%d"]),
    default=str(dt.datetime.today().date() - dt.timedelta(days=2)),
    show_default=True,
    help="Start date of VJ109GA NRT data to download.",
)
@click.option(
    "-e",
    "--end-date",
    type=click.DateTime(formats=["%Y%m%d", "%Y-%m-%d"]),
    default=str(dt.datetime.today().date() - dt.timedelta(days=1)),
    show_default=True,
    help="End date of VJ109GA NRT data to download.",
)
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(
        file_okay=False, dir_okay=True, writable=True, exists=False, path_type=Path
    ),
    default=VJ109GA_NRT_DIR,
    envvar="VJ109GA_NRT_DIR",
    show_default=True,
    help="Absolute directory to store VJ109GA granule files set by VJ109GA_NRT_DIR"
    " environment variable. Date subdirectories will be added (e.g. 2023.10.03).",
)
def get_nrt_data(start_date, end_date, output_dir):
    """
    Download VIIRS VJ109GA Near Real-Time data for a date range.

    Downloads data from NASA LANCE for each date in the range, organizing
    files into date-based subdirectories and setting appropriate permissions
    for shared PetaLibrary access.
    """
    for date in date_range(start_date=start_date, end_date=end_date):
        print(f"fetching for {date}")
        dated_output_dir = output_dir / date.strftime("%Y.%m.%d")
        dated_output_dir.mkdir(parents=True, exist_ok=True)
        get_data(date, LANCE_CONCEPT_ID, dated_output_dir)
        move_granules_to_date_dirs(dated_output_dir, output_dir)
        chmod_data(dated_output_dir)
        chown_data(dated_output_dir)


if __name__ == "__main__":
    """Executed from the command line"""
    get_nrt_data()
