#!/usr/bin/env python
# This fetched the final `daily surface reflectance` data

import datetime as dt
from pathlib import Path
import logging

import click

from src.fetch_nrt import move_granules_to_date_dirs
from src.fetch import chmod_data, chown_data, get_data
from src.util import date_range

from src.constants import (
    FILE_PERMISSIONS,
    get_final_dir,
)
from src.constants.products import PRODUCT_LANCE_CONFIG_FINAL

# configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

SUPPORTED_FINAL_PRODUCTS = list(PRODUCT_LANCE_CONFIG_FINAL.keys())


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
    default=str(dt.datetime.today().date() - dt.timedelta(days=2)),
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
    type=click.Choice(SUPPORTED_FINAL_PRODUCTS, case_sensitive=False),
    multiple=True,
    default=["VJ109GA"],
    show_default=True,
    help="Which product to download",
)
def get_lp_data(start_date, end_date, output_dir, product):

    products = [p.upper() for p in product]
    total_files = 0

    for prod in products:
        short_name, concept_id = PRODUCT_LANCE_CONFIG_FINAL[prod]
        output_dir = get_final_dir(prod)
        output_dir.mkdir(parents=True, exist_ok=True)

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
