import glob
import os
import subprocess
from pathlib import Path

import click

from src.error import ScagDrfsFileError
from src.make_tif import make_tif
from src.mask_drfs import mask_drfs
from src.constants.products import SUPPORTED_PRODUCTS, PRODUCT_INPUT_DIR_ENVVAR
from src.run_drfs_idl import run_drfs_idl_via_bash
from src.constants.field_info import FIELD_BITDEPTHS, VALID_FIELD_NAMES
from src.util import (
    get_bitdepth_for_field_name,
    get_date_from_filename,
    get_field_name,
    get_tile_id_from_filename,
)


@click.command()
@click.option(
    "-h",
    "--src-file",
    required=True,
    type=click.Path(
        file_okay=True, dir_okay=False, writable=False, exists=True, path_type=Path
    ),
    help="Path to the source file to be processed.",
)
@click.option(
    "-c",
    "--component-dir",
    type=click.Path(
        file_okay=False, dir_okay=True, writable=True, exists=False, path_type=Path
    ),
    envvar="DRFS_COMPONENT_DIR",
    show_default=True,
    help="Directory containing necessary DRFS components.",
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
    "Defaults to environment variable WORK_DIR.",
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
    "--product",
    "-P",
    type=click.Choice(SUPPORTED_PRODUCTS, case_sensitive=False),
    default="MOD09GA",
    show_default=True,
    help="Input product to process (MOD09GA, VNP09GA, VJ109GA).",
)
def run_drfs(src_file, component_dir, working_dir, staging_dir, product):
    """Process the DRFS files: DELTAVIS, drfsGS, RF"""
    day = get_date_from_filename(src_file)
    tile = get_tile_id_from_filename(src_file)

    print(f"about to run_drfs() for {day=} and {tile=}", flush=True)
    print(f"Executing run_drfs_idl_via_bash() with:")
    print(f"  {src_file=}")
    print(f"  {component_dir=}")
    print(f"  {working_dir=}")
    print(f"  ...", flush=True)
    IDL_output = run_drfs_idl_via_bash(src_file, component_dir, working_dir)
    print(f"IDL_output for file {src_file}:\n{IDL_output}", flush=True)

    mask_drfs(
        tile_id=tile,
        date=day,
        src_file=src_file,
        working_dir=working_dir,
        staging_dir=staging_dir,
        product=product,
    )

    bip_files = list(working_dir.glob("**/*.bip.meta"))
    if len(bip_files) != 1:
        raise ScagDrfsFileError(
            "Found either zero or multiple BIP "
            "metadata files in working directory: " + str(working_dir)
        )
    bip_meta_file = bip_files[0]

    for unmask_file in glob.glob(os.path.join(working_dir, "*.Unmask")):
        field_name = get_field_name(unmask_file)
        bit_depth = get_bitdepth_for_field_name(field_name)
        output_tif = os.path.join(
            staging_dir, unmask_file.replace("bin.Unmask", "Unmask.tif")
        )
        print(
            f"Generating tif for:\n  unmask_file: {unmask_file}\n  field_name: {field_name}\n  bit_depth: {bit_depth}\n  output_tif: {output_tif}",
            flush=True,
        )
        make_tif(
            meta_file=bip_meta_file,
            input_file=unmask_file,
            depth=str(bit_depth),
            output_file=output_tif,
        )

    for mask_file in glob.glob(os.path.join(working_dir, "*.mask")):
        field_name = get_field_name(mask_file)
        bit_depth = get_bitdepth_for_field_name(field_name)
        output_tif = os.path.join(staging_dir, mask_file.replace("bin.mask", "tif"))
        print(
            f"Generating tif for:\n  mask_file: {mask_file}\n  field_name: {field_name}\n  bit_depth: {bit_depth}\n  output_tif: {output_tif}",
            flush=True,
        )
        make_tif(
            meta_file=bip_meta_file,
            input_file=mask_file,
            depth=str(bit_depth),
            output_file=output_tif,
        )

    print(f"Finished in run_drfs()")


if __name__ == "__main__":
    """Executed from the command line"""
    run_drfs()
