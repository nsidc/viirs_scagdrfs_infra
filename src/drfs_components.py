"""Loading functions for DRFS component files."""

import re
from pathlib import Path

import numpy as np

ZENITH_VALUES = [15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75]


def load_irradiance_arrays(
    comps_dir: Path, verbose: bool = True
) -> tuple[np.ndarray, np.ndarray]:
    """Load direct and diffuse irradiance arrays.

    Returns (dir_arr, dif_arr) each shape (216, 14, 19)
    """
    fn_direct = comps_dir / "CRB/direct.bin"
    direct = np.fromfile(fn_direct, dtype=np.float32)

    fn_total = comps_dir / "CRB/total.bin"
    total = np.fromfile(fn_total, dtype=np.float32)

    # IDL reform() uses column-major order, numpy needs order='F' to match
    dir_arr = direct.reshape(216, 14, 19, order="F")
    tot_arr = total.reshape(216, 14, 19, order="F")
    dif_arr = tot_arr - dir_arr

    logger.debug(f"Loaded direct irradiance from: {fn_direct}")
    logger.debug(f"Loaded difuse irradiance from: {fn_total}")

    return dir_arr, dif_arr


def load_modis_wavelengths(comps_dir: Path, verbose: bool = True) -> np.ndarray:
    """Load 7 MODIS band wavelengths. Shape: (7,)"""
    fn_modis_wavelengths = comps_dir / "MODIS.wvl"
    modis_wavelengths = np.loadtxt(fn_modis_wavelengths)
    logger.debug(f"Loaded modis_wavelengths from: {fn_modis_wavelengths}")

    return modis_wavelengths


def load_aviris_wavelengths(comps_dir: Path, verbose: bool = True) -> np.ndarray:
    """Load AVIRIS wavelengths. Shape: (2, 216)"""
    fn_aviris_wavelengths = comps_dir / "irrad10nm.wvl"
    aviris_wavelengths = np.loadtxt(fn_aviris_wavelengths).T
    logger.debug(f"Loaded aviris_wavelengths from: {fn_aviris_wavelengths}")

    return aviris_wavelengths


def load_ndgsi_lut(comps_dir: Path, sza: int, verbose: bool = True) -> np.ndarray:
    """Load NDGSI lookup table for a given SZA. Shape: (2, 110)"""
    fn_ndgsi_lut = comps_dir / f"MODIS.z{sza}.ndgsi"
    ndgsi_lut = np.loadtxt(fn_ndgsi_lut).T

    logger.debug(f"Loaded ndgsi lut for {sza} from: {fn_ndgsi_lut}")

    return ndgsi_lut


def load_sli(comps_dir: Path, sza: int, verbose: bool = True) -> np.ndarray:
    """Load clean snow SLI spectra for a given SZA. Shape: (7, 110)"""
    fn_sli = comps_dir / f"MODIS.z{sza}.sli"

    data_raw = np.fromfile(fn_sli, dtype=np.float32)
    data_first_7x110 = data_raw[: 7 * 110]
    data_110x7 = data_first_7x110.reshape(110, 7)
    data_7x110 = np.swapaxes(data_110x7, 0, 1)

    logger.debug(f"Loaded clean snow SLI for {sza} from: {fn_sli}")

    return data_7x110


def load_all_luts(comps_dir: Path, verbose: bool = True) -> dict:
    """Pre-load all LUTs at startup rather than inside the pixel loop."""
    return {
        sza: {
            "ndgsi": load_ndgsi_lut(comps_dir, sza, verbose),
            "sli": load_sli(comps_dir, sza, verbose),
        }
        for sza in ZENITH_VALUES
    }


def load_terrain(
    comps_dir: Path, h: str, v: str, verbose: bool = True
) -> tuple[np.ndarray, np.ndarray]:
    """Load slope and aspect arrays for a tile.

    Returns (slope, aspect) each shape (2400, 2400)
    """
    terrain_files = list((comps_dir / "DEM").glob(f"terrain_*_h{h}v{v}.bsq"))
    if len(terrain_files) != 1:
        raise RuntimeError(
            f"Expected 1 terrain file for h{h}v{v}, found {len(terrain_files)}: {terrain_files}"
        )
    # fn_dem = terrain_files[0]
    data = np.fromfile(terrain_files[0], dtype=np.float32).reshape(2, 2400, 2400)
    slope = data[0, :, :]
    aspect = data[1, :, :]

    logger.debug(
        f"Loaded terrain slope and aspect for h{h}v{v} from: {terrain_files[0]}"
    )

    return slope, aspect


def load_dem(comps_dir: Path, h: str, v: str, verbose: bool = True) -> np.ndarray:
    """Load DEM elevation in meters. Shape: (2400, 2400)"""
    dem_files = list((comps_dir / "DEM").glob(f"dem_*_h{h}v{v}.bsq"))
    if len(dem_files) != 1:
        raise RuntimeError(
            f"Expected 1 DEM file for h{h}v{v}, found {len(dem_files)}: {dem_files}"
        )
    dem_file = dem_files[0]
    dem_data = np.fromfile(dem_file, dtype=np.int16).reshape(2400, 2400)

    logger.debug(f"Loaded DEM data for h{h}v{v} from: {dem_file}")

    return dem_data


def parse_tile_id(tile: str) -> tuple[str, str]:
    """Parse 'h29v13' into ('29', '13')."""
    match = re.match(r"h(\d+)v(\d+)", tile)
    if not match:
        raise ValueError(f"Cannot parse tile ID: {tile}")
    return match.group(1), match.group(2)
