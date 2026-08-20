"""
GMTED2010 -> MODIS Sinusoidal grid pipeline
=============================================
For each MODIS tile (h, v) listed in a CSV, this script:
  1. Computes the tile's true lat/lon footprint.
  2. Finds every GMTED2010 30x20 degree tile that overlaps that footprint.
  3. Mosaics those GMTED tiles together.
  4. Reprojects/resamples the mosaic onto the exact MODIS sinusoidal grid
     for that h,v (2400x2400 @ ~463.31m by default).
  5. Computes slope (band 1) and aspect (band 2) via Horn's method
     (matches GDAL's `gdaldem slope/aspect` default algorithm).
  6. Writes elevation and slope/aspect as both GeoTIFF and ENVI/BSQ.

Expected GMTED folder/file structure (after unzipping, one folder per zip):
  GMTED_DIR/GMTED2010S70W180_150/70s180w_20101117_gmted_mea150.tif
  GMTED_DIR/GMTED2010N10E030_150/10n030e_20101117_gmted_mea150.tif
  ... etc.

Requires: rasterio, numpy, pandas, gdal

Running this script:
    To run this script use the following command after installing all libraries:

    python dem_processing.py --n-pixels 2400

    This will save data at 500m resolution. Change to --n-pixels 1200 for 1km resolution. 
"""

import os
import math
import argparse
import numpy as np
import pandas as pd
import rasterio
from rasterio.merge import merge
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.transform import from_origin
from rasterio.crs import CRS
from rasterio.io import MemoryFile
from osgeo import gdal

try:
    gdal.UseExceptions()
except Exception:
    pass

# ---------------------------------------------------------------------------
# CONFIG - edit these paths/settings for your setup
# ---------------------------------------------------------------------------
MODIS_TILE_XLSX = "VIIRS_tiles.xlsx"   # must have columns: h, v
MODIS_TILE_SHEET = "Additional" # "Top 100" or "Additional"
GMTED_DIR = "/scratch/alpine/lost1845/GMTED2010"                  # parent folder containing GMTED2010*_150 subfolders
OUTPUT_DIR = "/scratch/alpine/lost1845/GMTED2010/Output"
N_PIXELS = 2400                        # 2400 = 500m-class (463.31m actual); 1200 = 1km; 4800 = 250m
RESOLUTION_LABELS = {1200: "1km", 2400: "500m", 4800: "250m"}  # rough label used in output filenames
GMTED_PRODUCT_TAG = "mea"  # which GMTED2010 statistic to use: mea (mean), med (median), min, max, std, dsc (breakline), mds
RESAMPLING_METHOD = Resampling.bilinear  # bilinear for elevation; use nearest only if you need exact source values
NODATA_VALUE = -9999
DEBUG = True   # set True to print mosaic/bounds/overlap diagnostics for each tile

# ---------------------------------------------------------------------------
# MODIS sinusoidal grid constants
# ---------------------------------------------------------------------------
MODIS_CRS = CRS.from_proj4(
    "+proj=sinu +lon_0=0 +x_0=0 +y_0=0 +R=6371007.181 +units=m +no_defs"
)
X_MIN = -20015109.354
Y_MAX = 10007554.677
TILE_SIZE_M = 1111950.5196666666  # 10 degrees at equator, in meters


def modis_tile_transform(h, v, n_pixels=None):
    """Affine transform + CRS for a given MODIS h,v tile."""
    if n_pixels is None:
        n_pixels = N_PIXELS
    pixel_size = TILE_SIZE_M / n_pixels
    tile_xmin = X_MIN + h * TILE_SIZE_M
    tile_ymax = Y_MAX - v * TILE_SIZE_M
    transform = from_origin(tile_xmin, tile_ymax, pixel_size, pixel_size)
    return transform, MODIS_CRS, pixel_size


def modis_tile_latlon_bbox(h, v, n_pixels=None):
    """Geographic bbox (lat_min, lat_max, lon_min, lon_max) covering a MODIS tile.

    Uses rasterio's transform_bounds, which densifies edges internally
    (default densify_pts=21) so curvature of the sinusoidal projection
    doesn't cause missed GMTED tiles.
    """
    if n_pixels is None:
        n_pixels = N_PIXELS
    transform, crs, pixel_size = modis_tile_transform(h, v, n_pixels)
    xmin, ymax = transform * (0, 0)
    xmax, ymin = transform * (n_pixels, n_pixels)
    lon_min, lat_min, lon_max, lat_max = transform_bounds(
        crs, "EPSG:4326", xmin, ymin, xmax, ymax, densify_pts=21
    )
    return lat_min, lat_max, lon_min, lon_max


# ---------------------------------------------------------------------------
# GMTED2010 tile naming
# ---------------------------------------------------------------------------
def gmted_tile_id(lat_south, lon_west):
    """Given a tile's north edge lat and west edge lon, return (folder, file) names."""
    lat_hem_upper = "N" if lat_south >= 0 else "S"
    lon_hem_upper = "E" if lon_west >= 0 else "W"
    lat_abs = abs(lat_south)
    lon_abs = abs(lon_west)

    folder = f"GMTED2010{lat_hem_upper}{lat_abs:02d}{lon_hem_upper}{lon_abs:03d}_150"
    # inner filename uses lowercase hemisphere letters, same lat-then-lon order
    lat_hem_lower = "n" if lat_south >= 0 else "s"
    lon_hem_lower = "e" if lon_west >= 0 else "w"
    filename = f"{lat_abs:02d}{lat_hem_lower}{lon_abs:03d}{lon_hem_lower}_20101117_gmted_mea150.tif"
    return folder, filename


def gmted_bounds_from_id(lat_south, lon_west):
    """Geographic bounds of a GMTED tile given its south edge lat / west edge lon.

    Confirmed empirically: e.g. the 'N50' tile spans 50N-70N (south edge=50,
    extends north 20 degrees), NOT 30N-50N.
    """
    return lat_south, lat_south + 20, lon_west, lon_west + 30


def all_gmted_tile_ids():
    """Generate the full 96-tile global grid of (lat_south, lon_west) pairs."""
    lat_souths = [-70, -50, -30, -10, 10, 30, 50, 70]
    lon_wests = list(range(-180, 180, 30))
    return [(lat, lon) for lat in lat_souths for lon in lon_wests]


def find_gmted_tiles(lat_min, lat_max, lon_min, lon_max):
    """Return list of (folder, filename) for GMTED tiles overlapping the given bbox.

    Handles antimeridian-crossing bboxes: when lon_max < lon_min (e.g. a MODIS tile
    straddling +/-180 degrees), the true footprint is [lon_min, 180] U [-180, lon_max]
    rather than a single ordered range.
    """
    if lon_max < lon_min:
        lon_ranges = [(lon_min, 180.0), (-180.0, lon_max)]
    else:
        lon_ranges = [(lon_min, lon_max)]

    matches = []
    for lat_south, lon_west in all_gmted_tile_ids():
        g_lat_min, g_lat_max, g_lon_min, g_lon_max = gmted_bounds_from_id(lat_south, lon_west)
        if g_lat_min < lat_max and g_lat_max > lat_min:
            for lo, hi in lon_ranges:
                if g_lon_min < hi and g_lon_max > lo:
                    matches.append(gmted_tile_id(lat_south, lon_west))
                    break
    return matches


# ---------------------------------------------------------------------------
# Mosaic + reproject
# ---------------------------------------------------------------------------
def resolve_gmted_file(gmted_dir, folder, expected_filename, product_tag=GMTED_PRODUCT_TAG):
    """
    Find the actual GMTED file for a given tile folder, robust to case
    inconsistencies in USGS's internal filenames (e.g. '70N060E...' vs
    '70n060e...') and to folders containing multiple product statistics
    (mea, med, min, max, std, dsc, mds) rather than just 'mea'.
    """
    import glob

    path = os.path.join(gmted_dir, folder, expected_filename)
    if os.path.exists(path):
        return path

    folder_path = os.path.join(gmted_dir, folder)
    all_tifs = glob.glob(os.path.join(folder_path, "*.tif"))
    tag_suffix = f"_gmted_{product_tag}150.tif".lower()
    matches = [p for p in all_tifs if p.lower().endswith(tag_suffix)]

    if len(matches) == 1:
        print(f"NOTE: '{expected_filename}' not found as-cased in {folder_path}; "
              f"using '{os.path.basename(matches[0])}' instead (case-insensitive match).")
        return matches[0]
    elif len(matches) > 1:
        raise FileNotFoundError(
            f"Expected GMTED file not found: {path}\n"
            f"Multiple '{product_tag}' candidates in {folder_path}: {matches}"
        )
    else:
        raise FileNotFoundError(
            f"Expected GMTED file not found: {path}\n"
            f"No file ending in '{tag_suffix}' found in {folder_path}. "
            f"Files present: {[os.path.basename(p) for p in all_tifs]}"
        )


def mosaic_gmted_tiles(gmted_dir, tile_ids):
    """Open + merge the matched GMTED tiles into one in-memory raster."""
    paths = [resolve_gmted_file(gmted_dir, folder, filename) for folder, filename in tile_ids]

    srcs = [rasterio.open(p) for p in paths]
    mosaic_array, mosaic_transform = merge(srcs)
    src_crs = srcs[0].crs
    src_nodata = srcs[0].nodata
    for s in srcs:
        s.close()

    return mosaic_array[0], mosaic_transform, src_crs, src_nodata


def reproject_to_modis_tile(mosaic_array, mosaic_transform, src_crs, src_nodata,
                             h, v, n_pixels=None,
                             resampling=RESAMPLING_METHOD):
    if n_pixels is None:
        n_pixels = N_PIXELS
    dst_transform, dst_crs, pixel_size = modis_tile_transform(h, v, n_pixels)
    dst_array = np.full((n_pixels, n_pixels), NODATA_VALUE, dtype=np.float32)

    reproject(
        source=mosaic_array,
        destination=dst_array,
        src_transform=mosaic_transform,
        src_crs=src_crs,
        src_nodata=src_nodata,
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        dst_nodata=NODATA_VALUE,
        resampling=resampling,
    )
    return dst_array, dst_transform, dst_crs, pixel_size


# ---------------------------------------------------------------------------
# Slope / Aspect via GDAL's own DEMProcessing (same code path as the
# `gdaldem slope` / `gdaldem aspect` CLI tools - Horn's algorithm by default)
# ---------------------------------------------------------------------------
def calculate_slope_aspect_gdal(elev_path, tmp_dir, tag, nodata=NODATA_VALUE):
    """
    Runs gdal.DEMProcessing on an elevation GeoTIFF already on disk and
    returns (slope_array, aspect_array) as float32 numpy arrays.

    elev_path : path to the elevation GeoTIFF for this tile (already written)
    """
    slope_path = os.path.join(tmp_dir, f"{tag}_slope_tmp.tif")
    aspect_path = os.path.join(tmp_dir, f"{tag}_aspect_tmp.tif")

    # alg="Horn" is GDAL's default and matches `gdaldem slope/aspect` with no -alg flag
    gdal.DEMProcessing(
        slope_path, elev_path, "slope",
        alg="Horn", slopeFormat="degree", computeEdges=True,
    )
    gdal.DEMProcessing(
        aspect_path, elev_path, "aspect",
        alg="Horn", zeroForFlat=False, computeEdges=True,
    )

    with rasterio.open(slope_path) as ds:
        slope = ds.read(1).astype(np.float32)
        slope_nodata = ds.nodata
    with rasterio.open(aspect_path) as ds:
        aspect = ds.read(1).astype(np.float32)
        aspect_nodata = ds.nodata

    # re-tag nodata to match our pipeline's nodata value for consistent downstream handling
    if slope_nodata is not None:
        slope[slope == slope_nodata] = nodata
    if aspect_nodata is not None:
        aspect[aspect == aspect_nodata] = nodata
    # gdaldem aspect emits -9999 for flat areas when zeroForFlat is not set -- remap
    aspect[aspect == -9999] = nodata

    os.remove(slope_path)
    os.remove(aspect_path)
    return slope, aspect


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------
def write_geotiff(path, array, transform, crs, nodata=NODATA_VALUE, band_names=None):
    bands = array.shape[0] if array.ndim == 3 else 1
    data = array if array.ndim == 3 else array[np.newaxis, ...]
    with rasterio.open(
        path, "w", driver="GTiff",
        height=data.shape[1], width=data.shape[2], count=bands,
        dtype=data.dtype, crs=crs, transform=transform, nodata=nodata,
        compress="lzw",
    ) as dst:
        dst.write(data)
        if band_names:
            for i, name in enumerate(band_names, start=1):
                dst.set_band_description(i, name)


def write_envi_bsq(path_no_ext, array, transform, crs, nodata=NODATA_VALUE, band_names=None):
    """Writes .bsq (or .dat, per rasterio's ENVI driver naming) + matching .hdr."""
    bands = array.shape[0] if array.ndim == 3 else 1
    data = array if array.ndim == 3 else array[np.newaxis, ...]
    out_path = path_no_ext + ".bsq"
    with rasterio.open(
        out_path, "w", driver="ENVI",
        height=data.shape[1], width=data.shape[2], count=bands,
        dtype=data.dtype, crs=crs, transform=transform, nodata=nodata,
        interleave="bsq",
    ) as dst:
        dst.write(data)
        if band_names:
            for i, name in enumerate(band_names, start=1):
                dst.set_band_description(i, name)
    # rasterio writes the header as <out_path>.hdr


# ---------------------------------------------------------------------------
# CLI args
# ---------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(description="GMTED2010 -> MODIS sinusoidal grid pipeline")
    parser.add_argument(
        "--n-pixels", type=int, default=N_PIXELS, choices=[1200, 2400, 4800],
        help="Tile size in pixels: 1200=1km, 2400=500m-class (default), 4800=250m",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    args = parse_args()
    n_pixels = args.n_pixels
    print(f"Using n_pixels = {n_pixels}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tiles = pd.read_excel(MODIS_TILE_XLSX, sheet_name=MODIS_TILE_SHEET)

    # For testing on a single tile, change the line below to:
    #   for _, row in tiles.iloc[:1].iterrows():
    for _, row in tiles.iterrows():
        h, v = int(row["h"]), int(row["v"])
        tag = f"h{h:02d}v{v:02d}_{RESOLUTION_LABELS[n_pixels]}"
        print(f"[{tag}] processing...")

        lat_min, lat_max, lon_min, lon_max = modis_tile_latlon_bbox(h, v, n_pixels)
        gmted_ids = find_gmted_tiles(lat_min, lat_max, lon_min, lon_max)
        if not gmted_ids:
            print(f"[{tag}] WARNING: no GMTED tiles matched bbox "
                  f"({lat_min:.2f},{lat_max:.2f},{lon_min:.2f},{lon_max:.2f}) - skipping")
            continue
        print(f"[{tag}] using GMTED tiles: {[f for _, f in gmted_ids]}")

        mosaic_array, mosaic_transform, src_crs, src_nodata = mosaic_gmted_tiles(GMTED_DIR, gmted_ids)

        if DEBUG:
            mosaic_bounds = rasterio.transform.array_bounds(*mosaic_array.shape, mosaic_transform)
            dst_transform_dbg, dst_crs_dbg, _ = modis_tile_transform(h, v, n_pixels)
            dst_bounds_dbg = rasterio.transform.array_bounds(n_pixels, n_pixels, dst_transform_dbg)
            src_bounds_in_dst_crs = transform_bounds(src_crs, dst_crs_dbg, *mosaic_bounds)

            print(f"[{tag}] DEBUG mosaic shape: {mosaic_array.shape}, dtype: {mosaic_array.dtype}")
            print(f"[{tag}] DEBUG mosaic min/max: {mosaic_array.min()} / {mosaic_array.max()}")
            print(f"[{tag}] DEBUG mosaic nodata: {src_nodata}")
            print(f"[{tag}] DEBUG mosaic bounds (src crs): {mosaic_bounds}")
            print(f"[{tag}] DEBUG src_crs: {src_crs}")
            print(f"[{tag}] DEBUG dst bounds (sinusoidal meters): {dst_bounds_dbg}")
            print(f"[{tag}] DEBUG dst_crs: {dst_crs_dbg}")
            print(f"[{tag}] DEBUG source footprint reprojected into MODIS sinusoidal: {src_bounds_in_dst_crs}")
            overlaps = not (src_bounds_in_dst_crs[2] < dst_bounds_dbg[0] or
                             src_bounds_in_dst_crs[0] > dst_bounds_dbg[2] or
                             src_bounds_in_dst_crs[3] < dst_bounds_dbg[1] or
                             src_bounds_in_dst_crs[1] > dst_bounds_dbg[3])
            print(f"[{tag}] DEBUG does source overlap destination tile? {overlaps}")

        elev, dst_transform, dst_crs, pixel_size = reproject_to_modis_tile(
            mosaic_array, mosaic_transform, src_crs, src_nodata, h, v, n_pixels
        )

        tile_dir = os.path.join(OUTPUT_DIR, f"h{h:02d}v{v:02d}")
        os.makedirs(tile_dir, exist_ok=True)

        elev_base = os.path.join(tile_dir, f"{tag}_elevation")
        sa_base = os.path.join(tile_dir, f"{tag}_slope_aspect")

        # cast elevation to int16 - NODATA_VALUE (-9999) fits comfortably within int16's
        # range and is far outside any real elevation, so it's safe as a sentinel
        elev_int16 = np.round(elev).astype(np.int16)

        write_geotiff(elev_base + ".tif", elev_int16, dst_transform, dst_crs, band_names=["elevation_m"])
        write_envi_bsq(elev_base, elev_int16, dst_transform, dst_crs, band_names=["elevation_m"])

        slope, aspect = calculate_slope_aspect_gdal(elev_base + ".tif", tile_dir, tag)
        slope_aspect_stack = np.stack([slope, aspect], axis=0)

        write_geotiff(sa_base + ".tif", slope_aspect_stack, dst_transform, dst_crs,
                      band_names=["slope_deg", "aspect_deg"])
        write_envi_bsq(sa_base, slope_aspect_stack, dst_transform, dst_crs,
                        band_names=["slope_deg", "aspect_deg"])

        print(f"[{tag}] done -> {elev_base}.tif/.bsq, {sa_base}.tif/.bsq")

    print("All tiles processed.")


if __name__ == "__main__":
    main()