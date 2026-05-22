"""Geometry preprocessing for DRFS computation.

Translates the geometry section of MOD_DRFS_v1_2.pro to numpy.
"""

import numpy as np


def preprocess_geometry(
    solarzenith: np.ndarray,
    solarazimuth: np.ndarray,
    slope: np.ndarray,
    aspect: np.ndarray,
    dem: np.ndarray,
) -> dict:
    """Preprocess solar and terrain geometry arrays for DRFS computation.

    Inputs are raw arrays as read from file:
        solarzenith/azimuth: integer arrays scaled by 100 (e.g. 2453 = 24.53 degrees)
        slope/aspect: float arrays in degrees
        dem: integer array in meters

    Args:
        solarzenith: Raw solar zenith array, shape (2400, 2400)
        solarazimuth: Raw solar azimuth array, shape (2400, 2400)
        slope: Slope array in degrees, shape (2400, 2400)
        aspect: Aspect array in degrees, shape (2400, 2400)
        dem: DEM elevation in meters, shape (2400, 2400)

    Returns:
        dict with keys:
            solarzenith_deg: Solar zenith in degrees (float), shape (2400, 2400)
            solarzenith_int: Solar zenith in degrees (int), used for LUT lookup
            cosine_illumination_angle: shape (2400, 2400)
            elev_km: Elevation in km (int), shape (2400, 2400)
    """
    print(f'{solarzenith.shape=}')
    print(f'{solarazimuth.shape=}')
    print(f'{slope.shape=}')
    print(f'{aspect.shape=}')
    print(f'{dem.shape=}')

    solarzenith.tofile(f'solarzenith_{solarzenith.dtype}_2400x2400.dat')
    solarazimuth.tofile(f'solarazimuth{solarazimuth.dtype}_2400x2400.dat')
    slope.tofile(f'slope{slope.dtype}_2400x2400.dat')
    aspect.tofile(f'aspect{aspect.dtype}_2400x2400.dat')
    dem.tofile(f'dem{dem.dtype}_2400x2400.dat')

    deg_to_rad = np.pi / 180.0

    # Scale raw integer files to degrees
    # MODIS creates solar geometry files as 4-digit whole numbers
    # e.g. 2453 = 24.53 degrees
    solarzenith_deg = solarzenith * 0.01
    solarazimuth_deg = solarazimuth * 0.01

    # Convert to radians
    slope_rad = slope * deg_to_rad
    aspect_rad = aspect * deg_to_rad
    solar_az_rad = solarazimuth_deg * deg_to_rad
    sza_rad = solarzenith_deg * deg_to_rad

    # Compute cosine illumination angle
    cos_slope = np.cos(slope_rad)
    sin_slope = np.sin(slope_rad)
    cos_sza = np.cos(sza_rad)
    sin_sza = np.sin(sza_rad)

    cosine_illumination_angle = cos_sza * cos_slope + sin_sza * sin_slope * np.cos(
        solar_az_rad - aspect_rad
    )

    # DEM to km (integer, matching IDL FIX())
    elev_km = (dem * 0.001).astype(np.int32)

    # Integer solar zenith for LUT lookup (matching IDL FIX())
    solarzenith_int = solarzenith_deg.astype(np.int32)

    return {
        "solarzenith_deg": solarzenith_deg,
        "solarzenith_int": solarzenith_int,
        "cosine_illumination_angle": cosine_illumination_angle,
        "elev_km": elev_km,
    }


def load_solar_geometry(
    zenithfile: str, azimuthfile: str, ns: int = 2400, nl: int = 2400, verbose: bool=True
) -> tuple:
    """Load raw solar zenith and azimuth binary files.

    Args:
        zenithfile: Path to solar zenith binary file
        azimuthfile: Path to solar azimuth binary file
        ns: Number of samples (default 2400)
        nl: Number of lines (default 2400)

    Returns:
        (solarzenith, solarazimuth) each shape (ns, nl) as int16
    """
    solarzenith = np.fromfile(zenithfile, dtype=np.int16).reshape(ns, nl)
    solarazimuth = np.fromfile(azimuthfile, dtype=np.int16).reshape(ns, nl)
    if verbose:
        print(f'    Loaded solar zenith array from: {zenithfile}')
        print(f'    Loaded solar azimuth array from: {azimuthfile}')
    return solarzenith, solarazimuth
