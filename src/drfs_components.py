"""Loading functions for DRFS component files."""

import re
from pathlib import Path

import numpy as np
import logging
from osgeo import gdal

logger = logging.getLogger(__name__)

ZENITH_VALUES = [15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75]


def read_geotiff(gtiff_fn):
    """Return the data field in a geotiff"""
    gdal.UseExceptions()
    ds_gtiff = gdal.Open(str(gtiff_fn), gdal.GA_ReadOnly)
    gtiff_band = ds_gtiff.GetRasterBand(1)
    gtiff_field = gtiff_band.ReadAsArray()

    return gtiff_field


def load_irradiance_arrays(
    comps_dir: Path,
) -> tuple[np.ndarray, np.ndarray]:
    """Load direct and diffuse irradiance arrays.

    Returns (dir_arr, dif_arr) each shape (216, 14, 19)
    """
    fn_direct = comps_dir / "irradiance_arrays" / "direct_irradiance.bin"
    direct = np.fromfile(fn_direct, dtype=np.float32)

    fn_total = comps_dir / "irradiance_arrays" / "total_irradiance.bin"
    total = np.fromfile(fn_total, dtype=np.float32)

    # IDL reform() uses column-major order, numpy needs order='F' to match
    dir_arr = direct.reshape(216, 14, 19, order="F")
    tot_arr = total.reshape(216, 14, 19, order="F")
    dif_arr = tot_arr - dir_arr

    logger.debug(f"Loaded direct irradiance from: {fn_direct}")
    logger.debug(f"Loaded difuse irradiance from: {fn_total}")

    return dir_arr, dif_arr


def load_modis_wavelengths(comps_dir: Path) -> np.ndarray:
    """Load 7 MODIS band wavelengths. Shape: (7,)"""
    fn_modis_wavelengths = comps_dir / "MODIS.wvl"
    modis_wavelengths = np.loadtxt(fn_modis_wavelengths)
    logger.debug(f"Loaded modis_wavelengths from: {fn_modis_wavelengths}")

    return modis_wavelengths


def load_aviris_wavelengths(comps_dir: Path) -> np.ndarray:
    """Load AVIRIS wavelengths. Shape: (2, 216)"""
    fn_aviris_wavelengths = comps_dir / "irrad10nm.wvl"
    aviris_wavelengths = np.loadtxt(fn_aviris_wavelengths).T
    logger.debug(f"Loaded aviris_wavelengths from: {fn_aviris_wavelengths}")

    return aviris_wavelengths


def load_ndgsi_lut(comps_dir: Path, sza: int) -> np.ndarray:
    """Load NDGSI lookup table for a given SZA. Shape: (2, 110)"""
    fn_ndgsi_lut = comps_dir / "ndgsi_LUTs" / f"MODIS.z{sza}.ndgsi"
    ndgsi_lut = np.loadtxt(fn_ndgsi_lut).T

    logger.debug(f"Loaded ndgsi lut for {sza} from: {fn_ndgsi_lut}")

    return ndgsi_lut


def load_sli(comps_dir: Path, sza: int) -> np.ndarray:
    """Load clean snow SLI spectra for a given SZA. Shape: (7, 110)"""
    fn_sli = comps_dir / "spectral_libraries" / f"MODIS.z{sza}.sli"

    data_raw = np.fromfile(fn_sli, dtype=np.float32)
    data_first_7x110 = data_raw[: 7 * 110]
    data_110x7 = data_first_7x110.reshape(110, 7)
    data_7x110 = np.swapaxes(data_110x7, 0, 1)

    logger.debug(f"Loaded clean snow SLI for {sza} from: {fn_sli}")

    return data_7x110


def load_all_luts(comps_dir: Path) -> dict:
    """Pre-load all LUTs at startup rather than inside the pixel loop."""
    return {
        sza: {
            "ndgsi": load_ndgsi_lut(comps_dir, sza),
            "sli": load_sli(comps_dir, sza),
        }
        for sza in ZENITH_VALUES
    }


def load_terrain(
    comps_dir: Path,
    h: str,
    v: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Load slope and aspect arrays for a tile.

    Returns (slope, aspect) each shape (2400, 2400)
    """
    # The '*' in '...*.tif' is for a version string in the file name:
    #   eg: slope_h07v03_v0.tif
    slope_files = list((comps_dir / "slope").glob(f'slope_h{h}v{v}*.tif'))
    if len(slope_files) != 1:
        raise RuntimeError(
            f"Expected 1 slope file for h{h}v{v}, found {len(slope_files)}: {slope_files}"
        )
    slope_file = slope_files[0]
    slope = read_geotiff(slope_file)
    logger.debug(
        f"Loaded slope for h{h}v{v} from: {slope_file}"
    )

    # The '*' in '...*.tif' is for a version string in the file name:
    #   eg: aspect_h07v03_v0.tif
    aspect_files = list((comps_dir / "aspect").glob(f'aspect_h{h}v{v}*.tif'))
    if len(aspect_files) != 1:
        raise RuntimeError(
            f"Expected 1 aspect file for h{h}v{v}, found {len(aspect_files)}: {aspect_files}"
        )
    aspect_file = aspect_files[0]
    aspect = read_geotiff(aspect_file)
    logger.debug(
        f"Loaded aspect for h{h}v{v} from: {aspect_file}"
    )

    return slope, aspect


def load_dem(comps_dir: Path, h: str, v: str) -> np.ndarray:
    """Load DEM elevation in meters. Shape: (2400, 2400)"""
    # The '*' in '...*.tif' is for a version string in the file name:
    #   eg: elevation_h07v03_v0.tif
    elevation_files = list((comps_dir / "elevation").glob(f'elevation_h{h}v{v}*.tif'))
    if len(elevation_files) != 1:
        raise RuntimeError(
            f"Expected 1 elevation file for h{h}v{v}, found {len(elevation_files)}: {elevation_files}"
        )
    elevation_file = elevation_files[0]
    elevation = read_geotiff(elevation_file)
    logger.debug(
        f"Loaded elevation for h{h}v{v} from: {elevation_file}"
    )

    return elevation


def parse_tile_id(tile: str) -> tuple[str, str]:
    """Parse 'h29v13' into ('29', '13')."""
    match = re.match(r"h(\d+)v(\d+)", tile)
    if not match:
        raise ValueError(f"Cannot parse tile ID: {tile}")
    return match.group(1), match.group(2)


if __name__ == '__main__':
    import sys
    ifn = sys.argv[1]
    print(f'ifn: {ifn}')
    breakpoint()

    ofn = ifn.replace('.tif', '.dat')
    assert ifn != ofn

    field = read_geotiff(ifn)
    field.tofile(ofn)
    print(f'Wrote: {ofn}')
