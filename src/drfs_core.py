"""Core DRFS radiative forcing computation.

Translates MOD09GA_FORCE_WEIGHT_v1_2 from IDL to numpy.
"""

import numpy as np
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

from src.find_irspec_v1_2 import compute_irradiance

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

    TODO: The tower-masking aspect of this code (at SASP, SBSP, GMSP)
          is never triggered because h, v are '09', '05', not '9', '5'
    """
    b1, b2, b3, b4, b5, b6 = [b.copy() for b in [b1, b2, b3, b4, b5, b6]]

    if thresh == 1:
        # Tower validation sites for h09v05 — not masked
        SASP = (1203, 502)
        SBSP = (1200, 502)
        GMSP = (1459, 227)

        b3_thresh = ((b4 - b2) / 2) + b2
        veg_mask = b3 < b3_thresh

        # TODO: In python, h and v are '09' and '05'
        #       so maybe this condition is never satisfied?
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


def IDL_Spline(X, Y, T, sigma=1.0):
    """Reproduce IDL's spline() function"""
    # Source - https://stackoverflow.com/a/64266640
    # Posted by Swike
    # Retrieved 2026-06-18, License - CC BY-SA 4.0
    n = min(len(X), len(Y))
    if n <= 2:
        print("X and Y must be arrays of 3 or more elements.")
    if sigma != 1.0:
        sigma = min(sigma, 0.001)
    yp = np.zeros(2 * n)
    delx1 = X[1] - X[0]
    dx1 = (Y[1] - Y[0]) / delx1
    nm1 = n - 1
    # nmp = n+1
    delx2 = X[2] - X[1]
    delx12 = X[2] - X[0]
    c1 = -(delx12 + delx1) / (delx12 * delx1)
    c2 = delx12 / (delx1 * delx2)
    c3 = -delx1 / (delx12 * delx2)
    slpp1 = c1 * Y[0] + c2 * Y[1] + c3 * Y[2]
    deln = X[nm1] - X[nm1 - 1]
    delnm1 = X[nm1 - 1] - X[nm1 - 2]
    delnn = X[nm1] - X[nm1 - 2]
    c1 = (delnn + deln) / (delnn * deln)
    c2 = -delnn / (deln * delnm1)
    c3 = deln / (delnn * delnm1)
    slppn = c3 * Y[nm1 - 2] + c2 * Y[nm1 - 1] + c1 * Y[nm1]
    sigmap = sigma * nm1 / (X[nm1] - X[0])
    dels = sigmap * delx1
    exps = np.exp(dels)
    sinhs = 0.5 * (exps - 1 / exps)
    sinhin = 1 / (delx1 * sinhs)
    diag1 = sinhin * (dels * 0.5 * (exps + 1 / exps) - sinhs)
    diagin = 1 / diag1
    yp[0] = diagin * (dx1 - slpp1)
    spdiag = sinhin * (sinhs - dels)
    yp[n] = diagin * spdiag
    delx2 = X[1:] - X[:-1]
    dx2 = (Y[1:] - Y[:-1]) / delx2
    dels = sigmap * delx2
    exps = np.exp(dels)
    sinhs = 0.5 * (exps - 1 / exps)
    sinhin = 1 / (delx2 * sinhs)
    diag2 = sinhin * (dels * (0.5 * (exps + 1 / exps)) - sinhs)
    diag2 = np.concatenate([np.array([0]), diag2[:-1] + diag2[1:]])
    dx2nm1 = dx2[nm1 - 1]
    dx2 = np.concatenate([np.array([0]), dx2[1:] - dx2[:-1]])
    spdiag = sinhin * (sinhs - dels)
    for i in range(1, nm1):
        diagin = 1 / (diag2[i] - spdiag[i - 1] * yp[i + n - 1])
        yp[i] = diagin * (dx2[i] - spdiag[i - 1] * yp[i - 1])
        yp[i + n] = diagin * spdiag[i]
    diagin = 1 / (diag1 - spdiag[nm1 - 1] * yp[n + nm1 - 1])
    yp[nm1] = diagin * (slppn - dx2nm1 - spdiag[nm1 - 1] * yp[nm1 - 1])
    for i in range(n - 2, -1, -1):
        yp[i] = yp[i] - yp[i + n] * yp[i + 1]
    m = len(T)
    subs = np.repeat(nm1, m)
    s = X[nm1] - X[0]
    sigmap = sigma * nm1 / s
    j = 0
    for i in range(1, nm1 + 1):
        while T[j] < X[i]:
            subs[j] = i
            j += 1
            if j == m:
                break
        if j == m:
            break
    subs1 = subs - 1
    del1 = T - X[subs1]
    del2 = X[subs] - T
    dels = X[subs] - X[subs1]
    exps1 = np.exp(sigmap * del1)
    sinhd1 = 0.5 * (exps1 - 1 / exps1)
    exps = np.exp(sigmap * del2)
    sinhd2 = 0.5 * (exps - 1 / exps)
    exps = exps1 * exps
    sinhs = 0.5 * (exps - 1 / exps)
    spl = (yp[subs] * sinhd1 + yp[subs1] * sinhd2) / sinhs + (
        (Y[subs] - yp[subs]) * del1 + (Y[subs1] - yp[subs1]) * del2
    ) / dels
    if m == 1:
        return spl[0]
    else:
        return spl


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
    # Note: Verified that dir_arr(216, 14, 19) and dif_arr(216, 14, 19)
    #       are the same in python and IDL

    # Scale reflectances from integer (x1000) to float
    # rfl comes in as BIP (ns, nl, nb) from IDL — reshape to (nb, ns, nl)
    # Note: The IDL calculations are done on un-scaled TB fields,
    #       so here, we cause the b1-b6 fields to be scaled-by-1000 values
    b1 = np.round(rfl[:, :, 0] * 1000.0)
    b2 = np.round(rfl[:, :, 1] * 1000.0)
    b3 = np.round(rfl[:, :, 2] * 1000.0)
    b4 = np.round(rfl[:, :, 3] * 1000.0)
    b5 = np.round(rfl[:, :, 4] * 1000.0)
    b6 = np.round(rfl[:, :, 5] * 1000.0)

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

    # Note: confirmed that here, b1 (after veg) is same as IDL

    # Find valid pixels (b4 > 0 and b5 > 0)
    # Note: confirmed that this is the same as the 'pos' array in IDL
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
    # Note: confirmed that array ndsi is the same as the IDL version
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

    # Note: Confirmed that array snow array is same to IDL

    # Compute NDGSI where valid
    ndgsi[valid_mask] = (b4[valid_mask] - b5[valid_mask]) / (
        b4[valid_mask] + b5[valid_mask]
    )
    # Non-snow pixels get FLAG for ndgsi and cumwts
    ndgsi[snow == 0.0] = FLAG
    cumwts[snow == 0.0] = FLAG

    # Note: Confirmed that array ndgsi is same as IDL

    # AVIRIS wavelengths — first row, first 51 bands for VIS
    avi_wvl = aviris_wvl[0, :] * 1000  # convert um to nm

    # Find nearest SZA for each pixel
    nearest_sza = _find_nearest_sza(solarzenith_int)

    logger.debug("Starting radiative forcing computation...")
    logger.debug("check nearest_sza...")

    # Process per unique SZA to minimize LUT lookups
    for sza_val in ZENITH_VALUES:
        sza_mask = (nearest_sza == sza_val) & ~np.isclose(ndgsi, FLAG)
        logger.debug(
            f"num grid cells with sza: {sza_val}  {np.sum(np.where(sza_mask, 1, 0))}"
        )

        if not np.any(sza_mask):
            continue

        ndgsi_lut = luts[sza_val]["ndgsi"]  # shape (2, 110)
        sli_lut = luts[sza_val]["sli"]  # shape (7, 110)

        ndgsi_vals = ndgsi_lut[1, :]  # ndgsi values, shape (110,)
        grsz_vals = ndgsi_lut[0, :]  # grain size values, shape (110,)

        # Get pixel indices for this SZA
        rows, cols = np.where(sza_mask)

        # Note: i and j correspondence in Python and IDL
        #     i,j =>    5, 1070  in python
        #     i,j => 1070,    5  in IDL
        for idx in range(len(rows)):
            i, j = rows[idx], cols[idx]

            ndgsi_ij = ndgsi[i, j]
            sz = solarzenith_deg[i, j]
            elev_ij = elev_km[i, j]
            cia_ij = cosine_illumination_angle[i, j]

            # Grain size LUT lookup — mirrors IDL logic
            # SS confirmed that the following three conditions are called the same number of times
            # in IDL and python
            # confirmed  array grnsz is same as IDL except machine precision
            if ndgsi_ij > ndgsi_vals[109]:
                grnsz[i, j] = (
                    grsz_vals[109]
                    + np.float32(
                        np.float32(ndgsi_ij - ndgsi_vals[109])
                        / np.float32(ndgsi_vals[109] - ndgsi_vals[108])
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
                    + np.float32(
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
                # This was the original conversion, using scipy.interpolate.CubicSpline()
                # cs = CubicSpline(modis_wvl[0:4], weights)
                # splineweights = cs(avi_wvl[0:51]) / 10000
                splineweights = (
                    IDL_Spline(modis_wvl[0:4], weights, avi_wvl[0:51]) / 10000
                )

                # Compute irradiance
                irrad = compute_irradiance(
                    solar_zenith_angle=sz,
                    elev=float(elev_ij),
                    cosine_illumination_angle=cia_ij,
                    dir_arr=dir_arr,
                    dif_arr=dif_arr,
                    verbose=False,
                )

                # Deltavis and forcing
                irrad_vis = irrad[0:51]
                total_irrad = np.sum(irrad_vis)
                if total_irrad != 0:
                    deltavis[i, j] = (
                        np.sum(splineweights * irrad_vis) / total_irrad
                    ) * 100
                forcing[i, j] = np.sum(splineweights * irrad_vis)

    # confirmed  array cumwts is same as IDL except machine precision
    # confirmed  array deltavis is same as IDL except machine precision
    # confirmed  array forcing is same as IDL except machine precision

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
