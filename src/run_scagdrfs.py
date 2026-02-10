import datetime as dt
import glob
import os
import subprocess
from datetime import timedelta
from pathlib import Path

import click
from dask.distributed import Client
from dask_jobqueue import SLURMCluster

from scagdrfs_infra.error import ScagDrfsDateRangeError
from scagdrfs_infra.output_to_peta import copy_output_to_peta
from scagdrfs_infra.output_to_v0 import copy_output_to_v0
from scagdrfs_infra.run_a_day import run_a_day
from scagdrfs_infra.util import (
    date_range,
    datetime_to_date,
    get_list_of_defined_regions,
    get_region_tile_ids,
    check_expected_tif_files_with_glob,
)


def setup_scagdrfs_cluster():
    # NOTE: account "ucb544_peak2" is set to expire Aug 7, 2026
    cluster = SLURMCluster(
        shebang="#!/usr/bin/bash",
        account="ucb544_peak2",
        cores=5,
        memory="10GB",
        walltime="03:00:00",
        death_timeout="1200",
        local_directory=f"{os.path.join(os.environ.get('WORK_DIR'), 'dask')}",
        # NOTE: name this based on which subroutine called it
        job_extra_directives=[
            "--qos=normal",
            "--job-name=scagdrfs",
            "--partition=amilan",
        ],
        log_directory=f"{os.path.join(os.environ.get('WORK_DIR'), 'dask', 'jobqueue-logs')}",
    )
    # NOTE: This scale should be at least 30 so that run_scag() can
    #       process 30 pic files at a time
    cluster.scale(30)

    print(cluster.job_script(), "\n")
    return cluster


@click.command()
@click.option(
    "-s",
    "--start-date",
    type=click.DateTime(formats=["%Y%m%d", "%Y-%m-%d"]),
    default=str(dt.datetime.today().date() - timedelta(days=1)),
    show_default=True,
    help="Start date of MOD09GA tiles to process.",
    callback=datetime_to_date,
)
@click.option(
    "-e",
    "--end-date",
    type=click.DateTime(formats=["%Y%m%d", "%Y-%m-%d"]),
    default=str(dt.datetime.today().date() - timedelta(days=1)),
    show_default=True,
    help="End date of MOD09GA tiles to process.",
    callback=datetime_to_date,
)
@click.option(
    "-r",
    "--regions",
    required=True,
    type=click.Choice(get_list_of_defined_regions(), case_sensitive=False),
    default=["us_alaska", "western_us", "nz_alps", "am_andes", "us"],
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
    "-i",
    "--input-dir",
    type=click.Path(file_okay=False, dir_okay=True, exists=False, path_type=Path),
    envvar="MOD09GA_NRT_DIR",
    show_default=True,
    help="Absolute directory to existing MOD09GA granule files set by MOD09GA_NRT_DIR"
    " environment variable. Date and tile ID subdirectories will be added"
    " (e.g. 2023.10.03/h08v04).",
)
@click.option(
    "-w",
    "--working-dir",
    type=click.Path(
        file_okay=False, dir_okay=True, writable=True, exists=False, path_type=Path
    ),
    envvar="WORK_DIR",
    show_default=True,
    help="Path to working directory where intermediate files are stored. "
    "Defaults to environment variable WORK_DIR. Date and tile ID subdirectories"
    " will be added (e.g. 2023.10.03/h08v04).",
)
@click.option(
    "-t",
    "--transfer-dir",
    type=click.Path(
        file_okay=False, dir_okay=True, writable=True, exists=False, path_type=Path
    ),
    envvar="PETALIB_TRANSFER_DIR",
    show_default=True,
    help="Path to data transfer directory where output files are stored before "
    "being transferred to the final V0 directory. Defaults to environment "
    "variable PETALIB_TRANSFER_DIR. Date and tile ID subdirectories will be "
    "added (e.g. 2023.10.03/h08v04).",
)
@click.option(
    "--no-publish",
    "-p",
    is_flag=True,
    help="This flag enables or disables copying files to PETA library then moving "
    "them to nusnow...publishing the outputs. Default is to publish.",
)
@click.pass_context
def run_scagdrfs(
    ctx,
    start_date,
    end_date,
    regions,
    skip,
    no_queue,
    input_dir,
    working_dir,
    transfer_dir,
    no_publish,
):
    # Forces a run even with 18 tifs should be a click option
    force_run_scagdrfs = False  # This should be false for normal Ops operations

    if end_date < start_date:
        raise ScagDrfsDateRangeError(
            "The start date of processing: "
            + start_date.strftime("%m/%d/%Y")
            + "  is after the end date: "
            + end_date.strftime("%m/%d/%Y")
        )

    orig_input_dir = input_dir
    orig_working_dir = working_dir
    orig_transfer_dir = transfer_dir

    if not no_queue:
        scagdrfs_cluster = setup_scagdrfs_cluster()
        scagdrfs_client = Client(scagdrfs_cluster)
        day_futures = []
    for day in date_range(start_date=start_date, end_date=end_date):
        tile_ids = get_region_tile_ids(regions)
        for tile in tile_ids:
            if input_dir == os.environ.get("MOD09GA_NRT_DIR"):
                input_dir = orig_input_dir / day.strftime("%Y.%m.%d")
            tif_dir = os.path.join(working_dir, day.strftime("%Y.%m.%d"), tile)
            tifCounter = check_expected_tif_files_with_glob(tif_dir, tile)
            if tifCounter and not force_run_scagdrfs:
                print(
                    f"You have all expected tif files in {tif_dir} skipping running {tile} for {day}.\n"
                )
            else:
                print(f"Running SCAGDRFS for day: {day}\n")
                if no_queue:
                    ctx.invoke(
                        run_a_day,
                        day=day,
                        input_dir=orig_input_dir,
                        working_dir=orig_working_dir,
                        staging_dir=orig_transfer_dir,
                        tile=tile,
                        skip=skip,
                        no_queue=no_queue,
                    )
                else:
                    cmd = (
                        ". {}/tasks/run-a-day.sh -d {} -i {} -w {} -s {} -t {}".format(
                            os.environ.get("TOPDIR"),
                            day,
                            orig_input_dir,
                            orig_working_dir,
                            orig_transfer_dir,
                            tile,
                        )
                    )
                    if skip:
                        cmd += " -k"
                    print(f"Running SCAGDRFS for day: {day} with command: \n{cmd}\n")
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
            print(f"Result from SCAGDRFS day run: {day_result} \n")
        # Close clients before closing the cluster that they were created on
        scagdrfs_client.close()
        scagdrfs_cluster.close()

    # move DRFS and SCAG output to petalibrary
    if not no_publish:
        print(
            f"Copying output to peta for {start_date} to {end_date} from {working_dir} to {transfer_dir} for {regions}"
        )
        copy_output_to_peta(
            start_date=start_date,
            end_date=end_date,
            input_dir=working_dir,
            output_dir=transfer_dir,
            regions=regions,
        )
        # move DRFS and SCAG output to v0
        v0_staging_dir = os.environ.get("V0_DIR")
        print(
            f"Copying output to V0 for {start_date} to {end_date} from {transfer_dir} to {v0_staging_dir} for {regions}"
        )
        copy_output_to_v0(
            start_date=start_date,
            end_date=end_date,
            transfer_dir=transfer_dir,
            output_dir=v0_staging_dir,
            tiles=tile_ids,
        )

    print(f"Finished run_scagdrfs() at {dt.datetime.now()}")


if __name__ == "__main__":
    """Executed from the command line"""
    run_scagdrfs()
