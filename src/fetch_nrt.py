#!/usr/bin/env python
"""Fetch VIIRS Near Real-Time (NRT) data from NASA LANCE."""

import datetime as dt
import logging
import sys

try:
    import click
except ModuleNotFoundError as e:
    print(
        f"ERROR: {e}\n"
        "Make sure you're running in the 'viirs' conda environment:\n"
        "  conda activate viirs"
    )
    sys.exit(1)

from src.fetch import chmod_data, chown_data, get_data
from src.util import date_range
from src.constants import (
    FILE_PERMISSIONS,
    SUPPORTED_PRODUCTS,
    PRODUCT_LANCE_CONFIG,
    get_nrt_dir,
)

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
        logger.warning(f"Skipping non-date folder: {dated_output_dir}")
        return

    moved_count = 0
    skipped_count = 0

    # Check both .h5 and .hdf files
    for f in list(dated_output_dir.glob("*.h5")) + list(dated_output_dir.glob("*.hdf")):
        parts = f.name.split(".")
        if len(parts) < 3:
            logger.warning(f"Skipping malformed filename: {f.name}")
            continue

        # Extract DOY from filename (e.g., A2024142 -> 2024142)
        file_doy = parts[1][1:]

        if file_doy == folder_doy:
            continue

        # Move to the correct folder
        try:
            correct_date = dt.datetime.strptime(file_doy, "%Y%j").strftime("%Y.%m.%d")
        except ValueError:
            logger.warning(f"Could not parse DOY from filename '{f.name}'")
            continue

        correct_folder = base_output_dir / correct_date
        correct_folder.mkdir(parents=True, exist_ok=True)
        dest = correct_folder / f.name

        if dest.exists():
            new_size = f.stat().st_size
            existing_size = dest.stat().st_size

            # Skip zero-byte files
            if new_size == 0 and existing_size != 0:
                logger.warning(f"Skipping 0-byte file: {f.name}")
                f.unlink()
                skipped_count += 1
                continue

            # Replace if newer
            if f.stat().st_mtime > dest.stat().st_mtime:
                logger.info(f"Replacing outdated file: {dest.name}")
                dest.unlink()
                f.rename(dest)
                dest.chmod(FILE_PERMISSIONS)
                moved_count += 1
            else:
                logger.info(f"File already exists and is up to date: {dest.name}")
                f.unlink()
                skipped_count += 1
        else:
            logger.info(f"Moving {f.name} -> {correct_folder}")
            f.rename(dest)
            dest.chmod(FILE_PERMISSIONS)
            moved_count += 1

    if moved_count > 0 or skipped_count > 0:
        logger.info(f"Moved {moved_count} files, skipped {skipped_count} files")


@click.command()
@click.option(
    "-s",
    "--start-date",
    type=click.DateTime(formats=["%Y%m%d", "%Y-%m-%d"]),
    default=str((dt.datetime.today() - dt.timedelta(days=2)).date()),
    show_default=True,
    help="Start date for VIIRS NRT data download.",
)
@click.option(
    "-e",
    "--end-date",
    type=click.DateTime(formats=["%Y%m%d", "%Y-%m-%d"]),
    default=str((dt.datetime.today() - dt.timedelta(days=1)).date()),
    show_default=True,
    help="End date for VIIRS NRT data download (inclusive).",
)
@click.option(
    "-P",
    "--product",
    type=click.Choice(SUPPORTED_PRODUCTS, case_sensitive=True),
    multiple=True,
    default=["VJ109GA"],
    show_default=True,
    help="Product(s) to download. Can be specified multiple times.",
)
def get_nrt_data(start_date, end_date, product):
    """
    Download Near Real-Time data for a date range.

    Downloads data from NASA LANCE for each date in the range, organizing
    files into date-based subdirectories and setting appropriate permissions
    for shared PetaLibrary access.

    Supports various products.
    """
    logger.info(f"Starting NRT download from {start_date.date()} to {end_date.date()}")

    products = [p.upper() for p in product]
    total_files = 0

    for prod in products:
        short_name, concept_id = PRODUCT_LANCE_CONFIG[prod]
        output_dir = get_nrt_dir(prod)
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"\n{'='*60}")
        logger.info(f"Downloading {short_name} (Concept ID: {concept_id})")
        logger.info(f"{'='*60}")
        product_files = 0

        for date in date_range(start_date=start_date, end_date=end_date):
            logger.info(f"Processing {prod} for {date.strftime('%Y-%m-%d')}")

            dated_output_dir = output_dir / date.strftime("%Y.%m.%d")
            dated_output_dir.mkdir(parents=True, exist_ok=True)

            files = get_data(date, concept_id, dated_output_dir, short_name)

            if files:
                move_granules_to_date_dirs(dated_output_dir, output_dir)
                chmod_data(dated_output_dir)
                chown_data(dated_output_dir)
                product_files += len(files)
                logger.info(
                    f"Successfully processed {len(files)} files for {date.strftime('%Y-%m-%d')}"
                )
            else:
                logger.warning(
                    f"No files downloaded for {short_name} on {date.strftime('%Y-%m-%d')}"
                )

        logger.info(f"{short_name} complete: {product_files} files downloaded")
        total_files += product_files

    logger.info(f"\n{'='*60}")
    logger.info(f"All downloads complete: {total_files} total files")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    get_nrt_data()
