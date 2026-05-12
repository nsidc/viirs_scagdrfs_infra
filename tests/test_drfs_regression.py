"""
Regression tests for MODIS DRFS NRT binary output files.

Primary use case: validating a Python reimplementation of the IDL pipeline
by comparing Python-generated outputs against IDL-generated golden files.

Because IDL and Python use different floating point implementations, byte-for-
byte hash comparison is not meaningful across languages. The scientifically
meaningful tests are:
    - Array shape + dtype
    - Pixel-level closeness (np.allclose)
    - Value statistics (min, max, mean, std)
    - Masked pixel counts

The hash test is kept but marked with a pytest mark so it can be selectively
run when comparing IDL-to-IDL outputs (e.g. testing that a pipeline run is
exactly reproducible), and skipped during IDL-to-Python validation.

File types for tile h09v05:
    RF        — Random Forest prediction      uint16  fill=2550
    drfsGS    — DRFS gap-filled / smoothed    uint16  fill=2550
    DELTAVIS  — delta visible                  uint8  fill=255

Each has two variants:
    *.bin.Unmask  — full unmasked array
    *.bin.mask    — ocean/snow/bad-QA pixels set to fill value

Run with:
    pytest tests/test_drfs_regression.py --date 20260309 --region onetile
"""

import ast
import configparser
import hashlib
from pathlib import Path
from typing import Optional

import numpy as np
import pytest

from src.constants.paths import TOPDIR, WORK_DIR, PETALIB_DIR

# ---------------------------------------------------------------------------
# File type configuration
# ---------------------------------------------------------------------------
FILE_CONFIGS: dict[str, dict] = {
    "RF": {
        "dtype": "uint16",
        "shape": (2400, 2400),
        "fill_value": 2550,
        "rtol": 1e-3,
        "atol": 1.0,
    },
    "drfsGS": {
        "dtype": "uint16",
        "shape": (2400, 2400),
        "fill_value": 2550,
        "rtol": 1e-3,
        "atol": 1.0,
    },
    "DELTAVIS": {
        "dtype": "uint8",
        "shape": (2400, 2400),
        "fill_value": 255,
        "rtol": 1e-3,
        "atol": 1.0,
    },
}

VERSION = "V01.1"
PRODUCT = "MOD09GANRT061"
FILE_TYPES = ["RF", "drfsGS", "DELTAVIS"]


def _file_variants(tile: str, date: str) -> list[dict]:
    def _base(file_type: str) -> str:
        return f"MODSCGDRF_NRT_{file_type}_{tile}_{PRODUCT}_{date}_{VERSION}"

    return [
        {
            "file_type": ft,
            "masked": masked,
            "filename": _base(ft) + (".bin.mask" if masked else ".bin.Unmask"),
        }
        for ft in FILE_TYPES
        for masked in (False, True)
    ]


# ===========================================================================
# Helpers
# ===========================================================================


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(path: Path, cfg: dict) -> np.ndarray:
    """Read a flat IDL-style binary file into a shaped numpy array."""
    arr = np.fromfile(path, dtype=cfg["dtype"])
    rows, cols = cfg["shape"]
    expected = rows * cols
    if arr.size != expected:
        raise ValueError(
            f"{path.name}: expected {expected} elements "
            f"({rows}×{cols} {cfg['dtype']}), got {arr.size}."
        )
    return arr.reshape(cfg["shape"])


def _valid_mask(arr: np.ndarray, fill_value: Optional[int]) -> np.ndarray:
    """Boolean mask of non-fill pixels."""
    valid = np.ones(arr.shape, dtype=bool)
    if fill_value is not None:
        valid &= arr != fill_value
    return valid


def _stats(arr: np.ndarray, fill_value: Optional[int]) -> dict:
    mask = _valid_mask(arr, fill_value)
    valid = arr[mask]
    return {
        "min": float(valid.min()) if valid.size else float("nan"),
        "max": float(valid.max()) if valid.size else float("nan"),
        "mean": float(valid.mean()) if valid.size else float("nan"),
        "std": float(valid.std()) if valid.size else float("nan"),
        "n_valid": int(mask.sum()),
        "n_fill": int((~mask).sum()),
    }


def _load_tiles(region: str) -> list[str]:
    """Read tile list for a region from tiles.ini, preserving key case."""
    tiles_ini = TOPDIR / "src" / "constants" / "tiles.ini"
    if not tiles_ini.exists():
        raise FileNotFoundError(f"tiles.ini not found at {tiles_ini}")
    cfg_ini = configparser.RawConfigParser()
    cfg_ini.optionxform = str  # preserve case so ONETILE != onetile
    cfg_ini.read(tiles_ini)
    if not cfg_ini.has_section("TILES"):
        raise ValueError(
            f"No [TILES] section in {tiles_ini}. "
            f"Sections found: {cfg_ini.sections()}"
        )
    region_upper = region.upper()
    if not cfg_ini.has_option("TILES", region_upper):
        available = [k for k in cfg_ini.options("TILES")]
        raise ValueError(
            f"Region '{region}' not found in tiles.ini. "
            f"Available: {', '.join(available)}"
        )
    return ast.literal_eval(cfg_ini.get("TILES", region_upper))


# ===========================================================================
# Parametrize
# ===========================================================================


def pytest_generate_tests(metafunc):
    """Parametrize over all tile+variant combinations for the given region."""
    if "tile_variant" not in metafunc.fixturenames:
        return

    region = metafunc.config.getoption("--region")
    date = metafunc.config.getoption("--date")

    # When regression flags aren't provided, collect 0 tests rather than error
    if region is None or date is None:
        metafunc.parametrize("tile_variant", [])
        return

    tiles = _load_tiles(region)
    combos = [
        {"tile": tile, **variant}
        for tile in tiles
        for variant in _file_variants(tile, date)
    ]
    ids = [
        f"{c['tile']}_{c['file_type']}_{'masked' if c['masked'] else 'unmasked'}"
        for c in combos
    ]
    metafunc.parametrize("tile_variant", combos, ids=ids)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture()
def golden_file(tile_variant, golden_dir_for):
    p = golden_dir_for(tile_variant["tile"]) / tile_variant["filename"]
    if not p.exists():
        pytest.skip(f"Golden file not found: {p}")
    return p


@pytest.fixture()
def output_file(tile_variant, output_dir_for):
    p = output_dir_for(tile_variant["tile"]) / tile_variant["filename"]
    if not p.exists():
        pytest.skip(f"Output file not found: {p}")
    return p


@pytest.fixture()
def cfg(tile_variant) -> dict:
    return FILE_CONFIGS[tile_variant["file_type"]]


@pytest.fixture()
def arrays(golden_file, output_file, cfg):
    return _load(golden_file, cfg), _load(output_file, cfg)


# ===========================================================================
# Tests
# ===========================================================================


class TestArrayShape:
    """Shape and dtype — should always match regardless of IDL vs Python."""

    def test_shape(self, arrays, cfg):
        golden_arr, output_arr = arrays
        assert (
            output_arr.shape == golden_arr.shape
        ), f"Shape mismatch: expected {golden_arr.shape}, got {output_arr.shape}"

    def test_dtype(self, output_file, cfg):
        arr = _load(output_file, cfg)
        assert arr.dtype == np.dtype(
            cfg["dtype"]
        ), f"dtype mismatch: expected {cfg['dtype']}, got {arr.dtype}"


class TestPixelCloseness:
    """
    Pixel-level closeness for valid (non-fill) pixels.

    Primary test for IDL -> Python validation. Checks that every valid pixel
    in the output is within tolerance of the corresponding golden pixel, and
    that fill pixels are in the same locations.
    """

    def test_valid_pixels_close(self, arrays, cfg):
        golden_arr, output_arr = arrays
        fill = cfg["fill_value"]
        rtol, atol = cfg["rtol"], cfg["atol"]

        golden_valid = _valid_mask(golden_arr, fill)
        output_valid = _valid_mask(output_arr, fill)

        if not np.array_equal(golden_valid, output_valid):
            n_diff = int((golden_valid != output_valid).sum())
            pytest.fail(
                f"Fill masks differ in {n_diff} pixels before closeness check. "
                "See TestMaskedPixelCounts for details."
            )

        g = golden_arr[golden_valid].astype(float)
        o = output_arr[output_valid].astype(float)
        close = np.allclose(g, o, rtol=rtol, atol=atol)

        if not close:
            diff = np.abs(g - o)
            pytest.fail(
                f"Pixel values not within tolerance (rtol={rtol}, atol={atol}).\n"
                f"  max absolute diff : {diff.max():.4g}\n"
                f"  mean absolute diff: {diff.mean():.4g}\n"
                f"  pixels outside tol: {int((diff > atol + rtol * np.abs(g)).sum()):,}"
            )


class TestValueStatistics:
    """
    Aggregate statistics of valid pixels.

    Useful as a quick summary when pixel-level closeness fails — tells you
    whether the outputs are in the right ballpark overall.
    """

    @pytest.fixture(autouse=True)
    def _compute(self, arrays, cfg):
        golden_arr, output_arr = arrays
        self.g = _stats(golden_arr, cfg["fill_value"])
        self.o = _stats(output_arr, cfg["fill_value"])
        self.rtol = cfg["rtol"]
        self.atol = cfg["atol"]

    def _assert_close(self, key: str):
        g, o = self.g[key], self.o[key]
        assert abs(o - g) <= self.atol + self.rtol * abs(g), (
            f"Statistic '{key}' out of tolerance: golden={g:.6g}, output={o:.6g} "
            f"(diff={abs(o-g):.4g})"
        )

    def test_min(self):
        self._assert_close("min")

    def test_max(self):
        self._assert_close("max")

    def test_mean(self):
        self._assert_close("mean")

    def test_std(self):
        self._assert_close("std")


class TestMaskedPixelCounts:
    """
    Valid and fill pixel counts must match exactly.

    A mismatch here means the pipeline is masking different pixels than the
    golden reference — likely a logic difference in the masking step.
    """

    def test_valid_pixel_count(self, arrays, cfg):
        golden_arr, output_arr = arrays
        g = _stats(golden_arr, cfg["fill_value"])
        o = _stats(output_arr, cfg["fill_value"])
        assert o["n_valid"] == g["n_valid"], (
            f"Valid pixel count mismatch: expected {g['n_valid']:,}, got {o['n_valid']:,} "
            f"(diff={abs(o['n_valid']-g['n_valid']):,})"
        )

    def test_fill_pixel_count(self, arrays, cfg):
        golden_arr, output_arr = arrays
        g = _stats(golden_arr, cfg["fill_value"])
        o = _stats(output_arr, cfg["fill_value"])
        assert o["n_fill"] == g["n_fill"], (
            f"Fill pixel count mismatch: expected {g['n_fill']:,}, got {o['n_fill']:,} "
            f"(diff={abs(o['n_fill']-g['n_fill']):,})"
        )


@pytest.mark.idl_only
class TestByteHash:
    """
    Byte-for-byte MD5 hash.

    Only meaningful when comparing IDL output to IDL output (e.g. verifying
    pipeline reproducibility). Will always fail when comparing IDL golden
    files to Python-generated output due to floating point differences.

    Run with:  pytest -v -m idl_only
    Skip with: pytest -v -m "not idl_only"   (default for Python port work)
    """

    def test_md5_matches_golden(self, golden_file, output_file):
        golden_hash = _md5(golden_file)
        output_hash = _md5(output_file)
        assert output_hash == golden_hash, (
            f"MD5 mismatch for {output_file.name}\n"
            f"  golden : {golden_hash}\n"
            f"  output : {output_hash}"
        )
