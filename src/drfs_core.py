"""Core DRFS radiative forcing computation.

Translates MOD09GA_FORCE_WEIGHT_v1_2 from IDL to numpy.
"""

import numpy as np
from pathlib import Path
from scipy.interpolate import CubicSpline

from src.find_irspec_v1_2 import compute_irradiance
from src.drfs_components import load_all_luts

FLAG = -9999.99
ZENITH_VALUES = np.array([15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75])


def _find_nearest_sza(sza_int: np.ndarray) -> np.ndarray:
    """For each pixel's integer SZA, find the nearest value in ZENITH_VALUES.

    Returns array of same shape with values from ZENITH_VALUES.
    """
    # For each pixel, find index of nearest zenith value
    # np.searchsorted finds insertion point; we check neighbors
    idx = np.searchsorted(ZENITH_VALUES, sza_int)
    idx = np.clip(idx, 0, len(ZENITH_VALUES) - 1)
    # Check if left neighbor is closer
    left_idx = np.maximum(idx - 1, 0)
    left_closer = np.abs(ZENITH_VALUES[left_idx] - sza_int) < np.abs(
        ZENITH_VALUES[idx] - sza_int
    )
    idx = np.where(left_closer, left_idx, idx)
    return ZENITH_VALUES[idx]


def _vegetation_mask(b1, b2, b3, b4, b5, b6, h, v, thresh):
    """Apply vegetation mask, returning masked copies of band arrays.

    Mirrors the vegetation masking logic in MOD09GA_FORCE_WEIGHT_v1_2.
    """
    b1, b2, b3, b4, b5, b6 = [b.copy() for b in [b1, b2, b3, b4, b5, b6]]

    if thresh == 1:
        # Tower validation sites for h09v05 — not masked
        SASP = (1203, 502)
        SBSP = (1200, 502)
        GMSP = (1459, 227)

        b3_thresh = ((b4 - b2) / 2) + b2
        veg_mask = b3 < b3_thresh

        if h == "9" and v == "5":
            # Preserve tower locations
            tower_mask = np.zeros((2400, 2400), dtype=bool)
            tower_mask[SASP] = True
            tower_mask[SBSP] = True
            tower_mask[GMSP] = True
            veg_mask = veg_mask & ~tower_mask

        for band in [b1, b2, b3, b4, b5, b6]:
            band[veg_mask] = FLAG

    return b1, b2, b3, b4, b5, b6


def compute_drfs(
    rfl: np.ndarray,
    solarzenith_deg: np.ndarray,
    solarzenith_int: np.ndarray,
    cosine_illumination_angle: np.ndarray,
    elev_km: np.ndarray,
    modis_wvl: np.ndarray,
    aviris_wvl: np.ndarray,
    luts: dict,
    dir_arr: np.ndarray,
    dif_arr: np.ndarray,
    h: str,
    v: str,
    thresh: int = 1,
    ns: int = 2400,
    nl: int = 2400,
) -> dict:
    """Compute DRFS radiative forcing fields.

    Args:
        rfl: BIP reflectance array, shape (7, 2400, 2400), scaled by 1000
        solarzenith_deg: Solar zenith in degrees (float), shape (2400, 2400)
        solarzenith_int: Solar zenith in degrees (int), shape (2400, 2400)
        cosine_illumination_angle: shape (2400, 2400)
        elev_km: Elevation in km (int), shape (2400, 2400)
        modis_wvl: MODIS band wavelengths, shape (7,)
        aviris_wvl: AVIRIS wavelengths, shape (2, 216)
        luts: dict from load_all_luts()
        dir_arr: Direct irradiance array, shape (216, 14, 19)
        dif_arr: Diffuse irradiance array, shape (216, 14, 19)
        h: Horizontal tile index string e.g. '9'
        v: Vertical tile index string e.g. '5'
        thresh: Vegetation threshold flag (1=use, 0=skip)
        ns: Number of samples
        nl: Number of lines

    Returns:
        dict with keys: ndgsi, ndsi, snow, grnsz, cumwts, deltavis, forcing
        each shape (2400, 2400)
    """
    # Scale reflectances from integer (x1000) to float
    # rfl comes in as BIP (ns, nl, nb) from IDL — reshape to (nb, ns, nl)
    b1 = rfl[0, :, :] * 1.0
    b2 = rfl[1, :, :] * 1.0
    b3 = rfl[2, :, :] * 1.0
    b4 = rfl[3, :, :] * 1.0
    b5 = rfl[4, :, :] * 1.0
    b6 = rfl[5, :, :] * 1.0

    # Initialize output arrays with FLAG
    ndsi = np.full((ns, nl), FLAG, dtype=np.float32)
    ndgsi = np.full((ns, nl), FLAG, dtype=np.float32)
    snow = np.full((ns, nl), FLAG, dtype=np.float32)
    grnsz = np.full((ns, nl), FLAG, dtype=np.float32)
    cumwts = np.full((ns, nl), FLAG, dtype=np.float32)
    deltavis = np.full((ns, nl), FLAG, dtype=np.float32)
    forcing = np.full((ns, nl), FLAG, dtype=np.float32)

    # Apply vegetation mask
    b1, b2, b3, b4, b5, b6 = _vegetation_mask(b1, b2, b3, b4, b5, b6, h, v, thresh)

    # Find valid pixels (b4 > 0 and b5 > 0)
    valid_mask = (b4 > 0) & (b5 > 0)
    if not np.any(valid_mask):
        print("NO SNOW FOUND, RETURNING FLAGGED BUNDLE")
        return {
            "ndgsi": ndgsi,
            "ndsi": ndsi,
            "snow": snow,
            "grnsz": grnsz,
            "cumwts": cumwts,
            "deltavis": deltavis,
            "forcing": forcing,
        }

    # Compute NDSI where valid
    ndsi[valid_mask] = (b2[valid_mask] - b6[valid_mask]) / (
        b2[valid_mask] + b6[valid_mask]
    )

    # Snow pixels: NDSI > 0.1 and b2 > 0.5
    snow_mask = (ndsi > 0.1) & (b2 > 0.5)
    if not np.any(snow_mask):
        print("NO SNOW FOUND, RETURNING FLAGGED BUNDLE")
        return {
            "ndgsi": ndgsi,
            "ndsi": ndsi,
            "snow": snow,
            "grnsz": grnsz,
            "cumwts": cumwts,
            "deltavis": deltavis,
            "forcing": forcing,
        }

    snow[valid_mask] = 0.0
    snow[snow_mask] = 1.0

    # Compute NDGSI where valid
    ndgsi[valid_mask] = (b4[valid_mask] - b5[valid_mask]) / (
        b4[valid_mask] + b5[valid_mask]
    )
    # Non-snow pixels get FLAG for ndgsi and cumwts
    ndgsi[snow == 0.0] = FLAG
    cumwts[snow == 0.0] = FLAG

    # AVIRIS wavelengths — first row, first 51 bands for VIS
    avi_wvl = aviris_wvl[0, :] * 1000  # convert um to nm

    # Find nearest SZA for each pixel
    nearest_sza = _find_nearest_sza(solarzenith_int)

    print("Starting radiative forcing computation...")

    # Process per unique SZA to minimize LUT lookups
    for sza_val in ZENITH_VALUES:
        sza_mask = (nearest_sza == sza_val) & (ndgsi != FLAG)
        if not np.any(sza_mask):
            continue

        ndgsi_lut = luts[sza_val]["ndgsi"]  # shape (2, 110)
        sli_lut = luts[sza_val]["sli"]  # shape (7, 110)

        ndgsi_vals = ndgsi_lut[1, :]  # ndgsi values, shape (110,)
        grsz_vals = ndgsi_lut[0, :]  # grain size values, shape (110,)

        # Get pixel indices for this SZA
        rows, cols = np.where(sza_mask)

        for idx in range(len(rows)):
            i, j = rows[idx], cols[idx]
            ndgsi_ij = ndgsi[i, j]
            sz = solarzenith_deg[i, j]
            elev_ij = elev_km[i, j]
            cia_ij = cosine_illumination_angle[i, j]

            # Grain size LUT lookup — mirrors IDL logic
            if ndgsi_ij > ndgsi_vals[109]:
                grnsz[i, j] = (
                    grsz_vals[109]
                    + (
                        (ndgsi_ij - ndgsi_vals[109])
                        / (ndgsi_vals[109] - ndgsi_vals[108])
                    )
                    * 10.0
                )
                cleanspec = sli_lut[:, 109]
            elif ndgsi_ij < ndgsi_vals[0]:
                grnsz[i, j] = grsz_vals[0]
                cleanspec = sli_lut[:, 0]
            else:
                luthigh = np.searchsorted(ndgsi_vals, ndgsi_ij, side="left")
                lutlow = luthigh - 1
                lutlow = np.clip(lutlow, 0, 108)
                luthigh = np.clip(luthigh, 1, 109)

                grnsz[i, j] = (
                    grsz_vals[lutlow]
                    + (
                        (ndgsi_ij - ndgsi_vals[lutlow])
                        / (ndgsi_vals[luthigh] - ndgsi_vals[lutlow])
                    )
                    * 10.0
                )

                # Clean MODIS spectrum interpolation
                cleanspec = sli_lut[:, lutlow] + (
                    (ndgsi_ij - ndgsi_vals[lutlow])
                    / (ndgsi_vals[luthigh] - ndgsi_vals[lutlow])
                ) * (sli_lut[:, lutlow] - sli_lut[:, luthigh])

                if i == 0 and j == 1871:
                    print(f"DEBUG pixel (0,1871):")
                    print(f"  ndgsi_ij: {ndgsi_ij}")
                    print(f"  cleanspec: {cleanspec}")
                    print(f"  sza_val: {sza_val}")
                    print(f"  lutlow: {lutlow} luthigh: {luthigh}")

                # Spectral ratio and weights
                rfl_pixel = np.array(
                    [b1[i, j], b2[i, j], b3[i, j], b4[i, j], b5[i, j], b6[i, j]]
                )
                rfl_scaled = (
                    rfl_pixel * 1000.0
                )  # match IDL integer scale to cleanspec scale
                specratio = cleanspec[3] / rfl_scaled[3] if rfl_scaled[3] != 0 else 1.0
                cumwts[i, j] = np.sum(cleanspec[0:3] - rfl_scaled[0:3] * specratio)
                weights = cleanspec[0:4] - rfl_scaled[0:4] * specratio

                # Spline interpolation from MODIS to AVIRIS wavelengths
                cs = CubicSpline(modis_wvl[0:4], weights)
                splineweights = cs(avi_wvl[0:51]) / 10000

                # Compute irradiance
                irrad = compute_irradiance(
                    solar_zenith_angle=sz,
                    elev=float(elev_ij),
                    cosine_illumination_angle=cia_ij,
                    dir_arr=dir_arr,
                    dif_arr=dif_arr,
                )

                # Deltavis and forcing
                irrad_vis = irrad[0:51]
                total_irrad = np.sum(irrad_vis)
                if total_irrad != 0:
                    deltavis[i, j] = (
                        np.sum(splineweights * irrad_vis) / total_irrad
                    ) * 100
                forcing[i, j] = np.sum(splineweights * irrad_vis)

                if i == 0 and j == 1871:
                    print(f"  rfl_scaled: {rfl_scaled[:4]}")
                    print(f"  specratio: {specratio:.6f}")
                    print(f"  weights: {weights}")
                    print(f"  splineweights[0:5]: {splineweights[0:5]}")
                    print(f"  irrad_vis[0:5]: {irrad_vis[0:5]}")
                    print(f"  total_irrad: {total_irrad:.4f}")
                    print(
                        f"  deltavis: {(np.sum(splineweights * irrad_vis) / total_irrad) * 100:.4f}"
                    )

                    print(
                        f"avi_wvl[0]: {avi_wvl[0]} avi_wvl[50]: {avi_wvl[50]}"
                    )  # should be 350-850nm
                    print(f"irrad[0:5]: {irrad[0:5]}")
                    print(f"irrad[50:55]: {irrad[50:55]}")
                    print(f"irrad[100:105]: {irrad[100:105]}")
                    print(f"irrad[200:205]: {irrad[200:205]}")
                    print("Radiative forcing computation complete.")

                    print(f"aviris_wvl shape: {aviris_wvl.shape}")
                    print(
                        f"aviris_wvl[0, 0:5]: {aviris_wvl[0, 0:5]}"
                    )  # first row first 5
                    print(
                        f"aviris_wvl[1, 0:5]: {aviris_wvl[1, 0:5]}"
                    )  # second row first 5

    return {
        "ndgsi": ndgsi,
        "ndsi": ndsi,
        "snow": snow,
        "grnsz": grnsz,
        "cumwts": cumwts,
        "deltavis": deltavis,
        "forcing": forcing,
    }


def write_drfs_outputs(
    results: dict,
    working_dir: Path,
    filename_prefix: str,
) -> None:
    """Write DRFS output .dat files matching IDL output format.

    Args:
        results: dict from compute_drfs()
        working_dir: Directory to write output files
        filename_prefix: e.g. 'MOD09GA.A2026068.h09v05.061.2026069014006.NRT'
    """
    outputs = {
        "deltavis": results["deltavis"],
        "forcing": results["forcing"],
        "drfs.grnsz": results["grnsz"],
    }
    for field, data in outputs.items():
        outpath = working_dir / f"{filename_prefix}.{field}.dat"
        data.astype(np.float32).tofile(outpath)
        print(f"Wrote {outpath}")
