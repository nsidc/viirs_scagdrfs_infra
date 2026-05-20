import re
import subprocess
from pathlib import Path

from src.constants.paths import TOPDIR


def invoke_idl_drfs(
    component_path,
    filename_prefix,
    working_dir,
    ns,
    nl,
    nb,
    date,
    year,
    horizontal,
    vertical,
    thresh,
):
    """call to system and return the stdout and stderr of that call"""
    idl_startup_batch = f"{TOPDIR}/scripts/drfs_idl_startup.bat"
    idl_bash_script = f"{TOPDIR}/scripts/drfs_bash_commands"
    # TODO: Consider wrapping this shell command in timeout so that
    #       it doesn't run forever if there is an IDL error.  Perhaps 20min?
    # NOTE: The shell call to idl requires that the config/env.sh script has
    #       been executed -- because it loads the IDL module for alpine and
    #       sets several shell environment variables -- but this is accomplished
    #       in run-drfs.sh and therefore does not need to happen here.
    cmd_idl = f"idl {idl_bash_script} -idl_startup {idl_startup_batch} -args {filename_prefix} {working_dir} {component_path} {ns} {nl} {nb} {date} {year} {horizontal} {vertical} {thresh}"

    print(f"cmd_idl:\n{cmd_idl}")

    try:
        cmd_idl_result = subprocess.run(
            cmd_idl,
            shell=True,
            capture_output=True,
            text=True,
            executable="/usr/bin/bash",
        )
        cmd_idl_string = f"Ran cmd_idl: {cmd_idl}\n  cmd_idl output: {cmd_idl_result}"
        cmd_idl_string = ""
        cmd_idl_string += f"cmd_idl: {cmd_idl}"
        cmd_idl_string += f"  stdout: {cmd_idl_result.stdout}"
        cmd_idl_string += f"  stderr: {cmd_idl_result.stderr}"
        cmd_idl_string += f""
    except Exception as e:
        cmd_idl_string = ""
        cmd_idl_string += f"cmd_idl: {cmd_idl}"
        cmd_idl_string += f"     stdout: {cmd_idl_result.stdout}"
        cmd_idl_string += f"     stderr: {cmd_idl_result.stderr}"
        cmd_idl_string += f"  Exception: {e}"
        cmd_idl_string += f""

    return cmd_idl_string


def run_drfs_idl_via_bash(hdf_file, component_dir, working_dir):
    """
    This routine uses the system IDL instead of the idlpy "bridge"
    because idlpy is limited to Python version 2.7, 3.5, or 3.6
    on CU's alpine supercomputer.

    Per the set of dash commands -- ./scripts/drfs_bash_commands --
    the command line command to invoke IDL is a single line:

        idl drfs_bash_commands -idl_startup drfs_idl_startup.bat
        -args <dir_with_IDL_code> <filename_prefix> <working_dir>
        <component_dir_with_slash> <ns> <nl> <nb> <date> <year>
        <modis_tile_h> <modis_tile_v> <thresh>

    eg:
        idl drfs_bash_commands -idl_startup drfs_idl_startup.bat
        -args MOD09GA.A2025090.h08v04.061.2025091013655.NRT
        /scratch/alpine/scotts/scagdrfs/working/2025.03.31/h08v04
        /pl/active/daac-production/jpl_DRFS_Components/ 2400 2400 7
        001 1900 08 04 1

    The hdf_file passed to here is of the form:
        {working_dir}/{filename_prefix}.hdf
    ...so both working_dir and filename_prefex are easily derived from it
        MOD09GA.A2025090.h08v04.061.2025091013655.NRT.hdf
        MOD09GA.A2025090.h08v04.061.2025091013655.NRT
    """
    # NOTE: working_dir should == hdf_file.parent
    filename_prefix = hdf_file.stem

    # Get information from the BIP metadata file.
    meta_path = Path(str(hdf_file).replace(hdf_file.suffix, ".bip.meta"))

    # Create the .bip and .bip_meta file if it does not exist
    if not meta_path.is_file():
        from scag.scripts.BIPifier import bipify_file
        bip_path = Path(str(hdf_file).replace(hdf_file.suffix, ".bip"))
        bipify_file(hdf_file, bip_path)
    meta_content = None
    with meta_path.open() as meta_file:
        meta_content = meta_file.read()
    if meta_content is None:
        raise RuntimeError(
            "Cannot read BIP metadata file: {bip_file}".format(bip_file=meta_path)
        )
    match = re.search("NLINES=(\d+)", meta_content)
    # TODO: this calculation appears to assume square input grids
    nl = match.group(1)
    ns = match.group(1)
    match = re.search("NBANDS=(\d+)", meta_content)
    nb = match.group(1)
    match = re.search("ZONE_NUMBER=h(\d+)v(\d+)", meta_content)
    horizontal = match.group(1)
    vertical = match.group(2)
    date = "001"  # placeholder, not used
    year = "1900"  # placeholder, not used
    thresh = 1  # Set as a constant
    # NOTE: Because of the IDL code, the component directory
    #       MUST include the trailing slash

    # NOTE: This directory must end in a slash '/' for IDL purposes
    idl_components_dir = str(component_dir) + "/"

    print(f"About to call invoke_idl_drfs() with:")
    print(f"  {idl_components_dir=}")
    print(f"  {filename_prefix=}")
    print(f"  {working_dir=}")
    print(f"  {ns=}")
    print(f"  {nl=}")
    print(f"  {nb=}")
    print(f"  {date=}")
    print(f"  {year=}")
    print(f"  {horizontal=}")
    print(f"  {vertical=}")
    print(f"  {thresh=}")
    print(flush=True)

    idl_drfs_output = invoke_idl_drfs(
        idl_components_dir,
        filename_prefix,
        working_dir,
        ns,
        nl,
        nb,
        date,
        year,
        horizontal,
        vertical,
        thresh,
    )

    print(f"Returning!", flush=True)

    return idl_drfs_output
