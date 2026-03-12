import datetime as dt
import glob
import logging
import os
import subprocess
from datetime import timedelta
from pathlib import Path

import click
from dask.distributed import Client
from dask_jobqueue import SLURMCluster

from src.bipify_input_files import bipify_files
from src.copy_scag_ancillary import copy_scag_ancillary_files
# from scagdrfs_infra.error import ScagDrfsFileError
from src.move_tiles import copy_tile_file
# from scagdrfs_infra.run_drfs import run_drfs
# from scagdrfs_infra.netcdf import create_netcdf
from src.run_scag import run_scag

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def setup_day_cluster():
    logger.info("Setting up Dask cluster...")
    # NOTE: account "ucb544_peak2" is set to expire Aug 7, 2026
    cluster = SLURMCluster(
        shebang="#!/usr/bin/bash",
        account="ucb544_peak2",
        cores=5,
        memory="10GB",
        walltime="03:00:00",
        death_timeout="1200",
        local_directory=f"{os.path.join(os.environ.get('WORK_DIR'), 'dask')}",
        job_extra_directives=[
            "--qos=normal",
            "--job-name=scagdrfs-day",
            "--partition=amilan",
        ],
        log_directory=f"{os.path.join(os.environ.get('WORK_DIR'), 'dask', 'jobqueue-logs')}",
    )
    cluster.adapt(minimum_jobs=1, maximum_jobs=100)

    print(cluster.job_script(), "\n")
    return cluster


@click.command()
@click.option(
    "-d",
    "--day",
    type=click.DateTime(formats=["%Y%m%d", "%Y-%m-%d"]),
    default=str(dt.datetime.today().date() - timedelta(days=1)),
    show_default=True,
    help="Date of the day of the tiles to process.",
)
@click.option(
    "-s",
    "--staging-dir",
    type=click.Path(
        file_okay=False, dir_okay=True, writable=True, exists=False, path_type=Path
    ),
    envvar="STAGING_DIR",
    show_default=True,
    help="Path to staging directory where output files are stored before being"
    " transferred to the final directory. Defaults to environment variable STAGING_DIR."
    " Date and tile ID subdirectories will be added (e.g. 2023.10.03/h08v04).",
)
@click.option(
    "-t",
    "--tile",
    required=True,
    type=str,
    help="Tile to process.",
)
@click.option(
    "-k",
    "--skip",
    is_flag=True,
    help="Skip moving H5 files from peta library to working directory.",
)
@click.option(
    "-n", "--no-queue", is_flag=True, help="Do not run tasks in the SLURM queue."
)
@click.pass_context
def run_a_day(ctx, day, input_dir, working_dir, staging_dir, tile, skip, no_queue):

    # NOTE: In normal operation, all sections of this code should run
    #       Developers may set some of these flags to False to speed
    #       up debug iteration
    remove_intermediate_files = True

    logger.info("Running a day for %s with tile %s", day, tile)
    param_lists = []
    print(
        "original working dir: ",
        working_dir,
        "  work_dir: ",
        os.environ.get("WORK_DIR"),
        "\n",
    )
    add_to_work_dir = False
    original_work_dir = working_dir
    if str(working_dir) == os.environ.get("WORK_DIR"):
        add_to_work_dir = True
    add_to_staging_dir = False
    original_staging_dir = staging_dir
    if str(staging_dir) == os.environ.get("STAGING_DIR"):
        add_to_staging_dir = True
    tile_params = {}
    if add_to_work_dir:
        working_dir = original_work_dir / day.strftime("%Y.%m.%d") / tile
    if not working_dir.exists():
        working_dir.mkdir(parents=True, exist_ok=True)
    tile_params["working_dir"] = working_dir
    if add_to_staging_dir:
        staging_dir = original_staging_dir / day.strftime("%Y.%m.%d") / tile
    if not staging_dir.exists():
        staging_dir.mkdir(parents=True, exist_ok=True)
    tile_params["staging_dir"] = staging_dir

    # NOTE: maybe this is NOT the best method to find files. I feel like we can be more exact
    # grab files for day
    if not skip:
        copy_tile_file(
            move_date=day, input_dir=input_dir, output_dir=working_dir, tile=tile
        )
    h5_files = list(working_dir.glob("**/*.h5"))
    if len(h5_files) != 1:
        print(
            f"Found either zero or multiple files in working directory: {working_dir}\n"
        )
        print(f"This will not run until there is 1 file in {working_dir}\n")
        print('SKIPPING create_netcdf()')
        # print("An empty netcdf will be created.\n")
        # create_netcdf(
        #     day=day,
        #     tif_dir=working_dir,
        #     tile_id=tile,
        # )

    else:
        h5_file = h5_files[0]
        tile_params["h5_file"] = h5_file
        # bipify files
        bipify_files(input_dir=working_dir, output_dir=working_dir)
        bip_meta_files = list(working_dir.glob("**/*.bip.meta"))
        # if len(bip_meta_files) != 1:
        #     raise ScagDrfsFileError(
        #         "Found either zero or multiple BIP "
        #         "metadata files in working directory: " + str(working_dir)
        #     )
        bip_meta_file = bip_meta_files[0]
        tile_params["bip_meta_file"] = bip_meta_file
        print('SKIPPING DRFS_COMPONENT_DIR -> component_dir')
        #tile_params["component_dir"] = os.environ.get("DRFS_COMPONENT_DIR")
        copy_scag_ancillary_files(bip_meta_file=bip_meta_file, output_dir=working_dir)
        param_lists.append(tile_params)

        # Set up the dask clusters if they will be used
        if not no_queue:
            day_cluster = setup_day_cluster()
            day_client = Client(day_cluster)
            drfs_futures = []
            scag_futures = []


        for tile_params in param_lists:
            tifCounter0 = len(glob.glob(os.path.join(working_dir, "*.tif")))

            # Run DRFS and SCAG on the command line not in the supercomputer
            if no_queue:
                # NOTE: COMMENTING OUT DRFS FOR TESTING
                # TODO: re-DO assign "component_dir"
                # TODO: Uncomment later
                # skip drfs if there are 6 tifs present (masked and unmasked drfs)
                # if tifCounter0 != 6:
                #     print("Running DRFS for ", tile_params["h5_file"], "...\n")
                #     ctx.invoke(
                #         run_drfs,
                #         h5_file=tile_params["h5_file"],
                #         working_dir=tile_params["working_dir"],
                #         staging_dir=tile_params["staging_dir"],
                #         component_dir=tile_params["component_dir"],
                #     )

                # Always run scag
                ctx.invoke(
                    run_scag,
                    bip_file=tile_params["bip_meta_file"].with_suffix(""),
                    h5_file=tile_params["h5_file"],
                    working_dir=tile_params["working_dir"],
                )

            # Run DRFS and SCAG in the supercomputer queue
            else:  # this is the "not no_queue" condition; i.e. run on supercomputer with dask
                # if tifCounter0 != 6:
                #     print(
                #         "Submitting DRFS run to queue for ",
                #         tile_params["h5_file"],
                #         "...\n",
                #     )
                #     cmd_drfs = ". {}/tasks/run-drfs.sh -h {} -w {} -s {} -c {}".format(
                #         os.environ.get("TOPDIR"),
                #         tile_params["h5_file"],
                #         tile_params["working_dir"],
                #         tile_params["staging_dir"],
                #         tile_params["component_dir"],
                #     )
                #     print(f"DRFS command to run: {cmd_drfs} \n")
                #     drfs_results = []
                #     try:
                #         cmd_drfs_output = subprocess.run(
                #             cmd_drfs,
                #             shell=True,
                #             capture_output=True,
                #             text=True,
                #             executable="/usr/bin/bash",
                #         )
                #         cmd_drfs_string = f"Ran cmd_drfs: {cmd_drfs}\n  cmd_drfs_output: {str(cmd_drfs_output)}"
                #         drfs_results.append(cmd_drfs_string)
                #     except Exception as e:
                #         cmd_drfs_string = f"Ran cmd_drfs: {cmd_drfs}\n  cmd_drfs_output: {str(cmd_drfs_output)}\n  WITH EXCEPTION: {str(e)}"
                #         drfs_results.append(cmd_drfs_string)

                #     for drfs_result in drfs_results:
                #         print("DRFS process result: ", drfs_result, "\n")

                # Always run SCAG
                print(
                    "Submitting scag run to queue for ",
                    tile_params["h5_file"],
                    "...\n",
                )
                cmd_scag = ". {}/scripts/run-scag.sh -b {} -h {} -w {}".format(
                    os.environ.get("TOPDIR"),
                    tile_params["bip_meta_file"].with_suffix(""),
                    tile_params["h5_file"],
                    tile_params["working_dir"],
                )
                print("SCAG command to run: ", cmd_scag, "\n")

                try:
                    scag_result = subprocess.run(
                        cmd_scag,
                        shell=True,
                        capture_output=True,
                        text=True,
                        executable="/usr/bin/bash",
                    )
                    print(f"SCAG processing result: {scag_result}")
                except:
                    print(f"EXCEPTION running cmd_scag: {cmd_scag}")

            # Run a check to see if all the expected tifs exist
            tifCounter = len(glob.glob(os.path.join(working_dir, "*.tif")))
            if tifCounter == 18:
                if remove_intermediate_files:
                    # remove intermediary files
                    types = (
                        "*.pic",
                        "*.control",
                        "*.list",
                        "*models",
                        "*.dat",
                        "*.bin",
                    )
                    file_list = []
                    for t in types:
                        file_list.extend(glob.glob(os.path.join(working_dir, t)))
                    for f in file_list:
                        os.remove(f)
            else:
                print(f"You have {tifCounter} tif files in {working_dir}")

if __name__ == "__main__":
    """Executed from the command line"""
    run_a_day()
