#!/usr/bin/env python

import datetime as dt
from pathlib import Path
import logging

import click

from src.fetch_nrt import move_granules_to_date_dirs
from src.fetch import chmod_data, chown_data, get_data
from src.util import date_range

from src.constants import (
    VJ109GA_DIR,
    FILE_PERMISSIONS,
    LANCE_CONCEPT_ID_VJ1,
    PRODUCT_SHORT_NAME_VJ1,
)

# configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "-s",
    "--start-date",
    type=click.DateTime(formats=["%Y%m%d", "%Y-%m-%d"]),
    default=str(dt.datetime.today().date() - dt.timedelta(days=2)),
    show_default=True,
    help="Start date of data to download.",
)
@click.option(
    "-e",
    "--end-date",
    type=click.DateTime(formats=["%Y%m%d", "%Y-%m-%d"]),
    default=str(dt.datetime.today().date() - dt.timedelta(days=1)),
    show_default=True,
    help="End date of MOD09GA LP data to download.",
)
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(
        file_okay=False, dir_okay=True, writable=True, exists=False, path_type=Path
    ),
    default="VJ109GA_DIR",
    envvar="VJ109GA_DIR",
    show_default=True,
    help="Absolute directory to store  granule files"
    ". Date subdirectories will be added (e.g. 2023.10.03).",
)
@click.option(
    "-p",
    "--product",
    type=click.Choice(["VJ1"]),
    default="VJ1",
    show_default=True,
    help="Which product to download",
)
def get_lp_data(start_date, end_date, output_dir, product):

    products_to_fetch = []
    if product.upper() in "VJ1":
        products_to_fetch.append((PRODUCT_SHORT_NAME_VJ1, LANCE_CONCEPT_ID_VJ1))

    for short_name, concept_id in products_to_fetch:
        logger.info(f"\n{'='*60}")
        logger.info(f"Downloading {short_name} (Concept ID: {concept_id})")
        logger.info(f"{'='*60}")

        product_files = 0

        for date in date_range(start_date=start_date, end_date=end_date):

            logger.info(f"Processing {short_name} for {date.strftime('%Y-%m-%d')}")

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
    """Executed from the command line"""
    get_lp_data()
