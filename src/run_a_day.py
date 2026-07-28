import datetime as dt
import glob
from src.log_config import setup_logging
import logging
import os
import shutil
import subprocess
from datetime import timedelta
from pathlib import Path

import click

from src.bipify_input_files import bipify_files
from src.copy_scag_ancillary import copy_scag_ancillary_files

from src.move_tiles import copy_tile_file

from src.netcdf import create_netcdf
from src.run_scag import run_scag
from src.constants.products import (
    PRODUCT_FILE_EXTENSION,
    SUPPORTED_PRODUCTS,
)
from src.constants.paths import (
    WORK_DIR,
    STAGE_DIR,
    TOPDIR,
    get_nrt_dir,
    DRFS_COMPONENT_DIR,
)
from src.run_drfs_python import create_drfs_geotiffs

logger = logging.getLogger(__name__)


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
    "--product",
    "-P",
    type=click.Choice(SUPPORTED_PRODUCTS, case_sensitive=False),
    required=True,
    help="Input product to process (MOD09GA, VNP09GA, VJ109GA).",
)
@click.option(
    "-s",
    "--staging-dir",
    type=click.Path(
        file_okay=False, dir_okay=True, writable=True, exists=False, path_type=Path
    ),
    default=STAGE_DIR,
    show_default=True,
    help="Path to staging directory where output files are stored before being"
    " transferred to the final directory. Defaults to STAGE_DIR defined in"
    " src.constants.paths."
    " Platform, date and tile ID subdirectories will be added"
    "(e.g. VJ109GA/2023.10.03/h08v04).",
)
@click.option(
    "-w",
    "--working-dir",
    type=click.Path(
        file_okay=False, dir_okay=True, writable=True, exists=False, path_type=Path
    ),
    default=WORK_DIR,
    show_default=True,
    help="Path to working directory where intermediate files are written"
    " while the product is being created. Defaults to WORK_DIR defined in"
    " src.constants.paths."
    " Platform, date and tile ID subdirectories will be added"
    "(e.g. VJ109GA/2023.10.03/h08v04).",
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
def run_a_day(ctx, day, product, staging_dir, working_dir, tile, skip, no_queue):

    tile_params = {}

    working_dir = working_dir / product.upper() / day.strftime("%Y.%m.%d") / tile
    working_dir.mkdir(parents=True, exist_ok=True)
    tile_params["working_dir"] = working_dir

    logger.info("Running a day for %s with tile %s", day, tile)
    logger.info("  run_a_day working_dir: %s", working_dir)
    logger.info("  run_a_day default WORK_DIR: %s", WORK_DIR)

    staging_dir = staging_dir / product.upper() / day.strftime("%Y.%m.%d") / tile
    staging_dir.mkdir(parents=True, exist_ok=True)
    tile_params["staging_dir"] = staging_dir

    # TODO: Should tile_params["product"] be product.upper() ?
    tile_params["product"] = product

    input_dir = get_nrt_dir(product.upper())
    if not skip:
        copy_tile_file(
            move_date=day,
            input_dir=input_dir,
            output_dir=working_dir,
            tile=tile,
            product=product,
        )

    ext = PRODUCT_FILE_EXTENSION[product.upper()]
    src_files = list(working_dir.glob(f"**/*{ext}"))

    param_lists = []
    if len(src_files) != 1:
        print(
            f"Found either zero or multiple files in working directory: {working_dir}\n"
        )
        print(f"This will not run until there is 1 file in {working_dir}\n")
        print("SKIPPING create_netcdf()")
        print("An empty netcdf will be created.\n")
        create_netcdf(
            day=day,
            tif_dir=working_dir,
            tile_id=tile,
            product=product,
        )

    else:
        src_file = src_files[0]
        tile_params["src_file"] = src_file
        # bipify files
        bipify_files(input_dir=working_dir, output_dir=working_dir, product=product)
        bip_meta_files = list(working_dir.glob("**/*.bip.meta"))
        bip_meta_file = bip_meta_files[0]
        tile_params["bip_meta_file"] = bip_meta_file
        tile_params["component_dir"] = DRFS_COMPONENT_DIR
        copy_scag_ancillary_files(bip_meta_file=bip_meta_file, output_dir=working_dir)
        param_lists.append(tile_params)

        for tile_params in param_lists:
            tifCounter0 = len(glob.glob(os.path.join(working_dir, "*.tif")))

            # Run DRFS and SCAG on the command line not in the supercomputer
            if no_queue:
                # skip drfs if there are 6 tifs present (masked and unmasked drfs)
                DRFS_products = ("MOD09GA", "VJ109GA")
                if product.upper() in DRFS_products:
                    # TODO: We should check for specific tif file names, not a count
                    if tifCounter0 != 6:
                        print("Running DRFS for ", tile_params["src_file"], "...\n")
                        raise RuntimeError(
                            "We should be calling create_drfs_geotiffs() instead of"
                            " run_drfs()"
                        )
                        # ctx.invoke(
                        #     run_drfs,
                        #     src_file=tile_params["src_file"],
                        #     working_dir=tile_params["working_dir"],
                        #     staging_dir=tile_params["staging_dir"],
                        #     component_dir=tile_params["component_dir"],
                        # )
                else:
                    print(
                        f"Skipping DRFS calculation because {product.upper()=} not in {DRFS_products=}"
                    )

                SCAG_products = ("MOD09GA", "VJ109GA")
                if product.upper() in SCAG_products:
                    ctx.invoke(
                        run_scag,
                        bip_file=tile_params["bip_meta_file"].with_suffix(""),
                        src_file=tile_params["src_file"],
                        working_dir=tile_params["working_dir"],
                        product=product,
                    )
                else:
                    print(
                        f"Skipping SCAG calculation because {product.upper()=} not in {SCAG_products=}"
                    )

            # Run DRFS and SCAG in the supercomputer queue
            else:  # this is the "not no_queue" condition; i.e. run on supercomputer with dask
                DRFS_products = ("MOD09GA", "VJ109GA")
                if product.upper() in DRFS_products:
                    # TODO: We should check for specific tif file names, not a count
                    # if tifCounter0 != 6:
                    print("Forcing the running of DRFS (ignoring .tif count)")
                    if True or tifCounter0 != 6:
                        print(
                            "Submitting DRFS run to queue for ",
                            tile_params["src_file"],
                            "...\n",
                        )

                        drfs_result = create_drfs_geotiffs(
                            tile_params["src_file"],
                            tile_params["product"],
                            tile_params["working_dir"],
                            tile_params["staging_dir"],
                            tile_params["component_dir"],
                        )
                        print(f"{drfs_result=}")
                else:
                    print(
                        f"Skipping DRFS calculation because {product.upper()=} not in {DRFS_products=}"
                    )

                SCAG_products = ("MOD09GA", "VJ109GA")
                if product.upper() in SCAG_products:
                    print(
                        "Submitting scag run to queue for ",
                        tile_params["src_file"],
                        "...\n",
                    )
                    cmd_scag = (
                        ". {}/scripts/run-scag.sh -b {} -h {} -w {} -P {}".format(
                            TOPDIR,
                            tile_params["bip_meta_file"].with_suffix(""),
                            tile_params["src_file"],
                            tile_params["working_dir"],
                            tile_params["product"],
                        )
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
                    except RuntimeError:
                        print(f"EXCEPTION running cmd_scag: {cmd_scag}")
                else:
                    print(
                        f"Skipping SCAG calculation because {product.upper()=} not in {SCAG_products=}"
                    )

            create_netcdf(
                day=day,
                tif_dir=working_dir,
                tile_id=tile,
                product=product,
            )


if __name__ == "__main__":
    """Executed from the command line"""
    setup_logging(level=logging.DEBUG)
    run_a_day()
