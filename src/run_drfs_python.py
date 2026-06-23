"""Python implementation of DRFS processing.

Replaces run_drfs_idl_via_bash() with pure Python/numpy.
Kept separate from run_drfs.py until validated against IDL golden outputs.
"""

from pathlib import Path

import numpy as np

from src.drfs_components import (
    load_irradiance_arrays,
    load_modis_wavelengths,
    load_aviris_wavelengths,
    load_all_luts,
    load_terrain,
    load_dem,
    parse_tile_id,
)
from src.drfs_geometry import preprocess_geometry, load_solar_geometry
from src.drfs_core import compute_drfs, write_drfs_outputs
from src.drfs_hdf_solar import extract_hdf_solar_fields
from src.drfs_BIPifier import bipify_file_drfs
from src.moddrfs_cleanse import moddrfs_cleanse


def create_bip_file_drfs(src_file, bip_file_drfs):
    """Create the DRFS version of the .bip file.
    Unlike SCAG, this allows negative integer values"""
    bipify_file_drfs(src_file, bip_file_drfs)


def run_drfs_python(src_file: Path, component_dir: Path, working_dir: Path) -> str:
    """Run DRFS processing using Python/numpy instead of IDL.

    Args:
        src_file: Path to the MODIS HDF source file
        component_dir: Path to DRFS component files (jpl_DRFS_Components)
        working_dir: Path to working directory containing BIP and solar geometry files

    Returns:
        Status string for logging
    """
    filename_stem = src_file.stem
    print(f"run_drfs_python: processing {filename_stem}", flush=True)

    # --- Parse tile ID ---
    # e.g. MOD09GA.A2026068.h09v05.061... -> h='09', v='05'
    tile_part = filename_stem.split(".")[2]  # e.g. 'h09v05'
    h, v = parse_tile_id(tile_part)
    print(f"  tile: h{h}v{v}", flush=True)

    # --- Load component files ---
    print("  loading component files...", flush=True)
    dir_arr, dif_arr = load_irradiance_arrays(component_dir)
    modis_wvl = load_modis_wavelengths(component_dir)
    aviris_wvl = load_aviris_wavelengths(component_dir)
    luts = load_all_luts(component_dir)
    slope, aspect = load_terrain(component_dir, h, v)
    dem = load_dem(component_dir, h, v)
    print("  component files loaded.", flush=True)

    # --- Extract solar geometry from input file ---
    # This replaces IDL's command:
    #   drfs_hdf_solar,in_file=full_filename
    # This should generate the Solar .dat files that are read in below
    #   <...>.SolarZenith_1.dat
    #   <...>.SolarAzimuth_1.dat
    extract_hdf_solar_fields(src_file)

    # Write a python version of:
    #    create_bip = extract_modis_reflectance(file, bip) ; HDF file needs full path.  Inserted by AB, 9/3/13
    #    (in mod_drfs_v1_2.pro)
    bip_file_drfs = working_dir / f"{filename_stem}.drfs.bip"
    create_bip_file_drfs(src_file, bip_file_drfs)

    # --- Load solar geometry ---
    print("  loading solar geometry...", flush=True)
    zenith_file = working_dir / f"{filename_stem}.SolarZenith_1.dat"
    azimuth_file = working_dir / f"{filename_stem}.SolarAzimuth_1.dat"
    solarzenith_raw, solarazimuth_raw = load_solar_geometry(
        str(zenith_file), str(azimuth_file)
    )
    print("  solar geometry loaded.", flush=True)

    # --- Preprocess geometry ---
    print("  preprocessing geometry...", flush=True)
    geom = preprocess_geometry(
        solarzenith=solarzenith_raw,
        solarazimuth=solarazimuth_raw,
        slope=slope,
        aspect=aspect,
        dem=dem,
    )

    # --- Load BIP reflectance ---
    print("  loading BIP reflectance...", flush=True)
    if not bip_file_drfs.exists():
        raise FileNotFoundError(f"BIP file not found: {bip_file_drfs}")
    # BIP is (ns, nl, nb) — reshape to (nb, ns, nl) for compute_drfs
    bip_raw = np.fromfile(bip_file_drfs, dtype=np.int16).reshape(2400, 2400, 7)

    rfl = np.divide(bip_raw, 1000.0, dtype=np.float32)
    print("  BIP loaded.", flush=True)

    # --- Compute DRFS ---
    print('Calling compute_drfs()...', flush=True)
    results = compute_drfs(
        rfl=rfl,  # (7, 2400, 2400)
        solarzenith_deg=geom["solarzenith_deg"],  # (2400, 2400)
        solarzenith_int=geom["solarzenith_int"],  # (2400, 2400)
        cosine_illumination_angle=geom["cosine_illumination_angle"],  # (2400, 2400)
        elev_km=geom["elev_km"],  # (2400, 2400)
        modis_wvl=modis_wvl,  # (7,)
        aviris_wvl=aviris_wvl,  # (2, 216)
        luts=luts,  # keys: 15-75 by 5
        dir_arr=dir_arr,  # (216, 14, 19)
        dif_arr=dif_arr,  # (216, 14, 19)
        h=h,  # '09'
        v=v,  # '05'
        thresh=1,
    )
    print("  DRFS computation complete.", flush=True)

    # --- Write outputs ---
    print("  writing output files...", flush=True)
    write_drfs_outputs(
        results=results,
        working_dir=working_dir,
        filename_prefix=filename_stem,
    )

    # --- Cleanse the .dat files ---
    full_filename_prefix = Path(working_dir, filename_stem)
    moddrfs_cleanse(full_filename_prefix, 2400, 2400)

    return f"run_drfs_python completed for {filename_stem}"


if __name__ == "__main__":
    import click

    @click.command()
    @click.option("--src-file", required=True, type=click.Path(path_type=Path))
    @click.option("--component-dir", required=True, type=click.Path(path_type=Path))
    @click.option("--working-dir", required=True, type=click.Path(path_type=Path))
    def main(src_file, component_dir, working_dir):
        print('Running from run_drfs_python() __main__')
        print(f'  {src_file=}')
        print(f'  {component_dir=}')
        print(f'  {working_dir=}')
        result = run_drfs_python(src_file, component_dir, working_dir)
        print(result)

    main()
