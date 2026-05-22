import numpy as np

ZENITH_ARRAY = np.array(
    [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0, 55.0, 60.0, 65.0, 70.0]
)
ELEVATION_ARRAY = np.array(
    [
        0.0,
        0.5,
        1.0,
        1.5,
        2.0,
        2.5,
        3.0,
        3.5,
        4.0,
        4.5,
        5.0,
        5.5,
        6.0,
        6.5,
        7.0,
        7.5,
        8.0,
        8.5,
        9.0,
    ]
)


def _find_bounding_index(array, value):
    """Find the lower bounding index for value in array.

    Mirrors IDL's min(array - value, /absolute) pattern.
    """
    idx = np.argmin(np.abs(array - value))
    # If the nearest is above value, step down one
    if array[idx] > value:
        idx = max(0, idx - 1)
    # Clamp to second-to-last so idx+1 is always valid
    idx = min(idx, len(array) - 2)
    return idx


def find_irspec(
    sza: float, elev: float, dir_arr: np.ndarray, dif_arr: np.ndarray, verbose:bool=False
) -> np.ndarray:
    """Return weighted average direct and diffuse irradiance spectra
    for a given solar zenith angle and elevation.

    Args:
        sza: Solar zenith angle in degrees (5-70)
        elev: Elevation in km (0-9)
        dir_arr: Direct irradiance array, shape (216, 14, 19)
        dif_arr: Diffuse irradiance array, shape (216, 14, 19)

    Returns:
        Array of shape (2, 216) where [0, :] is direct and [1, :] is diffuse
    """
    z_sub = _find_bounding_index(ZENITH_ARRAY, sza)
    mini = ZENITH_ARRAY[z_sub]
    maxi = ZENITH_ARRAY[z_sub + 1]
    # Each SBDART spectrum is 5 degrees apart
    z_weight = 1 - ((maxi - sza) / 5)

    e_sub = _find_bounding_index(ELEVATION_ARRAY, elev)
    e_weight = 1 - ((ELEVATION_ARRAY[e_sub + 1] - elev) / 0.5)

    dir_min = dir_arr[:, z_sub, e_sub]
    dir_max = dir_arr[:, z_sub + 1, e_sub + 1]
    dif_min = dif_arr[:, z_sub, e_sub]
    dif_max = dif_arr[:, z_sub + 1, e_sub + 1]

    if verbose:
        print('in find_irspec()')
        dir_min.tofile(f'py_dir_min_{dir_min.shape}.dat')
        dir_max.tofile(f'py_dir_max_{dir_max.shape}.dat')
        dif_min.tofile(f'py_dif_min_{dif_min.shape}.dat')
        dif_max.tofile(f'py_dif_max_{dif_max.shape}.dat')

    direct_out = z_weight * (dir_max - dir_min) + dir_min
    diffuse_out = z_weight * (dif_max - dif_min) + dif_min

    return np.stack([direct_out, diffuse_out], axis=0)


def compute_irradiance(
    solar_zenith_angle: float,
    elev: float,
    cosine_illumination_angle: float,
    dir_arr: np.ndarray,
    dif_arr: np.ndarray,
    verbose: bool=False,
) -> np.ndarray:
    """Compute terrain- and geometry-corrected spectral irradiance.

    Args:
        solar_zenith_angle: Solar zenith angle in degrees
        elev: Elevation in km
        cosine_illumination_angle: Cosine of the illumination angle
        dir_arr: Direct irradiance array, shape (216, 14, 19)
        dif_arr: Diffuse irradiance array, shape (216, 14, 19)

    Returns:
        Corrected irradiance spectrum, shape (216,)
    """
    result = find_irspec(
        sza=solar_zenith_angle, elev=elev, dir_arr=dir_arr, dif_arr=dif_arr, verbose=verbose
    )
    direct_input = result[0, :]
    diffuse_input = result[1, :]
    return (cosine_illumination_angle * direct_input) + diffuse_input
