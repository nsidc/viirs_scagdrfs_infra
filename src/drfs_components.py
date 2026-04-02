"""Loading functions for DRFS component files."""

import re
from pathlib import Path

import numpy as np

ZENITH_VALUES = [15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75]


def load_irradiance_arrays(comps_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    """Load direct and diffuse irradiance arrays.

    Returns (dir_arr, dif_arr) each shape (216, 14, 19)
    where dimensions are (spectral_bands, solar_zenith_angles, elevations)
    """
    direct = np.fromfile(comps_dir / "CRB/direct.bin", dtype=np.float32).reshape(
        216, 14, 19
    )
    total = np.fromfile(comps_dir / "CRB/total.bin", dtype=np.float32).reshape(
        216, 14, 19
    )
    diffuse = total - direct
    return direct, diffuse


def load_modis_wavelengths(comps_dir: Path) -> np.ndarray:
    """Load 7 MODIS band wavelengths. Shape: (7,)"""
    return np.loadtxt(comps_dir / "MODIS.wvl")


def load_aviris_wavelengths(comps_dir: Path) -> np.ndarray:
    """Load AVIRIS wavelengths. Shape: (2, 216)"""
    return np.loadtxt(comps_dir / "irrad10nm.wvl")


def load_ndgsi_lut(comps_dir: Path, sza: int) -> np.ndarray:
    """Load NDGSI lookup table for a given SZA. Shape: (2, 110)"""
    return np.loadtxt(comps_dir / f"MODIS.z{sza}.ndgsi").T


def load_sli(comps_dir: Path, sza: int) -> np.ndarray:
    """Load clean snow SLI spectra for a given SZA. Shape: (7, 110)"""
    path = comps_dir / f"MODIS.z{sza}.sli"
    data = np.fromfile(path, dtype=np.float32)
    return data.reshape(7, -1)[:, :110]


def load_all_luts(comps_dir: Path) -> dict:
    """Pre-load all LUTs at startup rather than inside the pixel loop."""
    return {
        sza: {
            "ndgsi": load_ndgsi_lut(comps_dir, sza),
            "sli": load_sli(comps_dir, sza),
        }
        for sza in ZENITH_VALUES
    }


def load_terrain(comps_dir: Path, h: str, v: str) -> tuple[np.ndarray, np.ndarray]:
    """Load slope and aspect arrays for a tile.

    Returns (slope, aspect) each shape (2400, 2400)
    """
    pattern = list((comps_dir / "DEM").glob(f"terrain_*_h{h}v{v}.bsq"))
    if len(pattern) != 1:
        raise RuntimeError(
            f"Expected 1 terrain file for h{h}v{v}, found {len(pattern)}: {pattern}"
        )
    data = np.fromfile(pattern[0], dtype=np.float32).reshape(2400, 2400, 2)
    return data[:, :, 0], data[:, :, 1]


def load_dem(comps_dir: Path, h: str, v: str) -> np.ndarray:
    """Load DEM elevation in meters. Shape: (2400, 2400)"""
    pattern = list((comps_dir / "DEM").glob(f"dem_*_h{h}v{v}.bsq"))
    if len(pattern) != 1:
        raise RuntimeError(
            f"Expected 1 DEM file for h{h}v{v}, found {len(pattern)}: {pattern}"
        )
    return np.fromfile(pattern[0], dtype=np.int16).reshape(2400, 2400)


def parse_tile_id(tile: str) -> tuple[str, str]:
    """Parse 'h29v13' into ('29', '13')."""
    match = re.match(r"h(\d+)v(\d+)", tile)
    if not match:
        raise ValueError(f"Cannot parse tile ID: {tile}")
    return match.group(1), match.group(2)
