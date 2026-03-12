import os
import subprocess
from pathlib import Path

import click
from dask import compute, delayed
from dask.distributed import Client
from dask_jobqueue import SLURMCluster

from src.mask_scag import mask_scag
# from scagdrfs_infra.netcdf import create_netcdf
from src.constants.products import SUPPORTED_PRODUCTS, PRODUCT_FILE_EXTENSION
from src.util import get_date_from_filename, get_info_from_bip_file


# TODO: This function is not used:  setup_scag_cluster()
def setup_scag_cluster():
    # NOTE: account "ucb544_peak2" is set to expire Aug 7, 2026
    cluster = SLURMCluster(
        shebang="#!/usr/bin/bash",
        account="ucb544_peak2",
        cores=5,
        memory="10GB",
        walltime="01:00:00",
        local_directory=f"{os.path.join(os.environ.get('WORK_DIR'), 'dask')}",
        job_extra_directives=[
            "--qos=normal",
            "--job-name=scag-proc",
            "--partition=amilan",
        ],
        log_directory=f"{os.path.join(os.environ.get('WORK_DIR'), 'dask', 'scag', 'jobqueue-logs')}",
    )
    # cluster.adapt(minimum_jobs=1, maximum_jobs=50)
    # This should be 30 so that all 30 pic files can be created at once
    cluster.scale(30)

    return cluster


@click.command()
@click.option(
    "-b",
    "--bip-file",
    type=click.Path(file_okay=True, dir_okay=False, exists=True, path_type=Path),
    help="Band Interleaved by Pixel (BIP) file to process.",
)
@click.option(
    "-h",
    "--src-file",
    type=click.Path(file_okay=True, dir_okay=False, exists=True, path_type=Path),
    help="H5 or HDF file to process.",
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
def run_scag(bip_file, src_file, working_dir, product):

    scag_cluster = setup_scag_cluster()
    scag_client = Client(scag_cluster)

    control_files = list(working_dir.glob("**/*.control"))

    # $PM/scag/bin/scag MOD09GA.A2023244.h08v05.061.NRT.bip 7 2400 2400 $fil
    # scag/bin/scag BIP-file num-bands num-samples num-lines control-file
    # Usage: scag [OPTION...] IMGFILE NBANDS NSAMPLES NLINES CONTROLFILE
    bip_info = get_info_from_bip_file(bip_file.with_suffix(bip_file.suffix + ".meta"))

    def run_command(cmd):
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, executable="/usr/bin/bash"
        )
        result.check_returncode()
        return result.stdout

    ext = PRODUCT_FILE_EXTENSION[product.upper()]
    delayed_tasks = []
    for control_file in control_files:
        cmd = f"cd {working_dir}; {os.environ.get('TOPDIR')}/scag/bin/scag {bip_file.name} {bip_info['num_bands']} {bip_info['num_samples']} {bip_info['num_lines']} {control_file.name}"
        # Switch from delayed/compute to submit/gather
        # delayed_tasks.append(delayed(run_command)(cmd))
        delayed_task = scag_client.submit(run_command, cmd)
        delayed_tasks.append(delayed_task)

    # Switch from delayed/compute to submit/gather
    # results = compute(*delayed_tasks)
    results = scag_client.gather(delayed_tasks)

    for result in results:
        print("SCAG command result: ", result, "\n")

    pic_files = list(working_dir.glob("**/*.pic"))

    user = os.environ.get("USER")
    cmd_sort = f"cd {working_dir}; /projects/{user}/scagdrfs_infra/scag/bin/scag_sort 2eminput 3eminput modprty2 modprty3 {str(src_file).replace(f'{ext}', '.')} {bip_info['num_samples']} {bip_info['num_lines']}"
    result_sort = subprocess.run(
        cmd_sort, shell=True, capture_output=True, text=True, executable="/usr/bin/bash"
    )
    result_sort.check_returncode()
    print("SCAG sort command result: ", result_sort.stdout, "\n")

    # mask scag and create geotifs
    mask_scag(
        date=get_date_from_filename(src_file),
        working_dir=working_dir,
        tile=bip_info["tile_id"],
    )

    # # create netcdf files
    # create_netcdf(
    #     day=get_date_from_filename(src_file),
    #     tif_dir=working_dir,
    #     tile_id=bip_info["tile_id"],
    # )


if __name__ == "__main__":
    """Executed from the command line"""
    run_scag()
