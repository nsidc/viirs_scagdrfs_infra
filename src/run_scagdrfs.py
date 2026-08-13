import datetime as dt
import subprocess
from datetime import timedelta
from pathlib import Path

import click
from dask.distributed import Client
from dask_jobqueue import SLURMCluster

# from scagdrfs_infra.error import ScagDrfsDateRangeError
# from scagdrfs_infra.output_to_peta import copy_output_to_peta
# from scagdrfs_infra.output_to_v0 import copy_output_to_v0
from src.constants.paths import WORK_DIR, TOPDIR
from src.constants.products import SUPPORTED_PRODUCTS
from src.run_a_day import run_a_day
from src.util import (
    date_range,
    get_list_of_defined_regions,
    get_region_tile_ids,
    check_expected_tif_files_with_glob,
)

import logging
from src.log_config import setup_logging

logger = logging.getLogger(__name__)

MAX_CONCURRENT_TILES = 100


def setup_scagdrfs_cluster(n_workers):
    # NOTE: account "ucb544_peak2" is set to expire Aug 7, 2026
    cluster = SLURMCluster(
        shebang="#!/usr/bin/bash",
        account="ucb544_peak2",
        # cores/memory are dask's own accounting; job_cpu/job_mem are what
        # actually land in the #SBATCH directives. One dask worker per job
        # takes one tile, and run_scag's thread pool gets all 5 cores.
        cores=1,
        processes=1,
        memory="20GB",
        job_cpu=15,
        job_mem="10GB",
        walltime="03:00:00",
        death_timeout="1200",
        local_directory=str(WORK_DIR / "dask"),
        job_extra_directives=[
            "--qos=cpu-normal",
            "--job-name=scagdrfs",
            "--partition=acpu",
        ],
        log_directory=str(WORK_DIR / "dask" / "jobqueue-logs"),
    )
    # One worker per job, one tile per worker
    cluster.scale(n_workers)

    logger.debug("Dask job script:\n%s", cluster.job_script())

    print(cluster.job_script(), "\n")
    return cluster


@click.command()
@click.option(
    "-s",
    "--start-date",
    type=click.DateTime(formats=["%Y%m%d", "%Y-%m-%d"]),
    default=str(dt.datetime.today().date() - timedelta(days=1)),
    show_default=True,
    help="Start date of tiles to process.",
)
@click.option(
    "-e",
    "--end-date",
    type=click.DateTime(formats=["%Y%m%d", "%Y-%m-%d"]),
    default=str(dt.datetime.today().date() - timedelta(days=1)),
    show_default=True,
    help="End date of tiles to process.",
)
@click.option(
    "-r",
    "--regions",
    required=True,
    type=click.Choice(get_list_of_defined_regions(), case_sensitive=False),
    default=[
        "USWEST",
        "USALASKA",
        "amandes",
        "useast",
        "euralps",
        "canada",
        "ashimalaya",
        "nzalps",
    ],
    multiple=True,
    help="Regions of tiles to process. Defaults to list with Western US and Alaska.",
)
@click.option(
    "--skip",
    "-k",
    is_flag=True,
    help="Skip moving HDF files from peta library to working directory.",
)
@click.option(
    "--no-queue", "-n", is_flag=True, help="Do not run tasks in the SLURM queue."
)
@click.option(
    "--product",
    "-P",
    type=click.Choice(SUPPORTED_PRODUCTS, case_sensitive=False),
    default="VNP09GA",
    show_default=True,
    help="Input product to process (MOD09GA, VNP09GA, VJ109GA).",
)
@click.option(
    "-t",
    "--transfer-dir",
    type=click.Path(
        file_okay=False, dir_okay=True, writable=True, exists=False, path_type=Path
    ),
    # NOTE: this will change
    default=lambda: WORK_DIR,
    show_default=True,
    help="Path to data transfer directory where output files are stored before "
    "being transferred to the final V0 directory."
    "Date and tile ID subdirectories will be "
    "added (e.g. 2023.10.03/h08v04).",
)
@click.option(
    "--no-publish",
    "-p",
    is_flag=True,
    help="Skip copying output to PetaLibrary and V0." "Default is to publish.",
)
@click.pass_context
def run_scagdrfs(
    ctx,
    start_date,
    end_date,
    regions,
    skip,
    no_queue,
    transfer_dir,
    no_publish,
    product,
):
    setup_logging()
    # Forces a run even with 18 tifs should be a click option
    force_run_scagdrfs = False  # This should be false for normal Ops operations
    # Set to true since we are in development stage

    product = product.upper()
    orig_transfer_dir = transfer_dir
    tile_ids = get_region_tile_ids(regions)
    n_days = len(list(date_range(start_date=start_date, end_date=end_date)))
    n_tasks = len(tile_ids) * n_days

    if not no_queue:
        scagdrfs_cluster = setup_scagdrfs_cluster(min(n_tasks, MAX_CONCURRENT_TILES))
        scagdrfs_client = Client(scagdrfs_cluster)
        day_futures = []

    for day in date_range(start_date=start_date, end_date=end_date):
        logger.info(f"run_scagdrfs: loop day: {day}")
        for tile in tile_ids:
            logger.info(f"run_scagdrfs: tile: {tile}")
            tif_dir = WORK_DIR / product / day.strftime("%Y.%m.%d") / tile
            tif_count = check_expected_tif_files_with_glob(tif_dir, tile, product)
            if tif_count and not force_run_scagdrfs:
                logger.info(
                    f"All expected tif files in {tif_dir} skipping running {tile} for {day}.\n"
                )
                continue

            logger.info(f"Running SCAGDRFS for {product},day: {day}\n")

            if no_queue:
                # print("    in no_queue...")
                ctx.invoke(
                    run_a_day,
                    day=day,
                    product=product,
                    staging_dir=orig_transfer_dir,
                    tile=tile,
                    skip=skip,
                    no_queue=no_queue,
                )
            else:
                # print("    NOT in no_queue...")
                cmd = f". {TOPDIR}/scripts/run-a-day.sh -d {day} -s {transfer_dir} -t {tile} -P {product}"

                if skip:
                    cmd += " -k"
                logger.info(f"Running SCAGDRFS for day: {day} with command: {cmd}")
                future = scagdrfs_client.submit(
                    subprocess.run,
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    executable="/usr/bin/bash",
                    pure=False,
                )
                day_futures.append(future)
    if not no_queue:
        day_results = scagdrfs_client.gather(day_futures)
        for day_result in day_results:
            if day_result.returncode == 0:
                logger.info("Day run succeeded: %s", day_result.args)
            else:
                logger.error(
                    "Day run FAILED (rc=%d): %s", day_result.returncode, day_result.args
                )
            if day_result.stdout:
                logger.info("day run stdout:\n%s", day_result.stdout)
            if day_result.stderr:
                logger.info("day run stderr:\n%s", day_result.stderr)
        # Close clients before closing the cluster that they were created on
        scagdrfs_client.close()
        scagdrfs_cluster.close()

    # # move DRFS and SCAG output to petalibrary
    # if not no_publish:
    #     print(
    #         f"Copying output to peta for {start_date} to {end_date} from {working_dir} to {transfer_dir} for {regions}"
    #     )
    #     copy_output_to_peta(
    #         start_date=start_date,
    #         end_date=end_date,
    #         input_dir=working_dir,
    #         output_dir=transfer_dir,
    #         regions=regions,
    #     )
    #     # move DRFS and SCAG output to v0
    #     v0_staging_dir = os.environ.get("V0_DIR")
    #     print(
    #         f"Copying output to V0 for {start_date} to {end_date} from {transfer_dir} to {v0_staging_dir} for {regions}"
    #     )
    #     copy_output_to_v0(
    #         start_date=start_date,
    #         end_date=end_date,
    #         transfer_dir=transfer_dir,
    #         output_dir=v0_staging_dir,
    #         tiles=tile_ids,
    #     )

    logger.info(f"Finished run_scagdrfs() at {dt.datetime.now()}")


if __name__ == "__main__":
    """Executed from the command line"""
    run_scagdrfs()
