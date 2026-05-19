"""
Regression tests for VIIRS SCAG NRT binary output files.

Tests both stages of SCAG output:

    Stage 1 — Raw SCAG bins (output of scag_sort, before masking):
        grnsz (uint16), other, rms, rock, shade, snow, veg (all uint8)
        Filenames: VJ109GA_NRT.A{doy}.{tile}.002.{timestamp}.{field}.bin

    Stage 2 — Masked/unmasked outputs (output of mask_scag):
        GS (uint16), ICE, ROCK, SHADE, SNOW, VEG (all uint8)
        Each has .bin.mask and .bin.Unmask variants
        Filenames: VIRSCGDRF_NRT_{field}_{tile}_VJ109GANRT061_{date}_V01.1.bin.{mask_status}

Unlike DRFS, SCAG is pure Python + deterministic binary, so byte-exact
hash comparison (TestByteHash) IS meaningful for run-to-run reproducibility.

Run with:
    pytest tests/test_scag_regression.py --date 20260518 --region onenztile --product VJ109GA
"""

import ast
import configparser
import datetime
import hashlib
from pathlib import Path
from typing import Optional

import numpy as np
import pytest

from src.constants.paths import TOPDIR
from src.constants.products import PRODUCT_TIF_PATTERN

# ---------------------------------------------------------------------------
# File type configuration
# ---------------------------------------------------------------------------

# Stage 2: masked/unmasked VIRSCGDRF_NRT output files
MASKED_FILE_CONFIGS: dict[str, dict] = {
    "GS": {
        "dtype": "uint16",
        "shape": (2400, 2400),
        "fill_value": 2550,
        "rtol": 0,
        "atol": 0,
    },
    "ICE": {
        "dtype": "uint8",
        "shape": (2400, 2400),
        "fill_value": 255,
        "rtol": 0,
        "atol": 0,
    },
    "ROCK": {
        "dtype": "uint8",
        "shape": (2400, 2400),
        "fill_value": 255,
        "rtol": 0,
        "atol": 0,
    },
    "SHADE": {
        "dtype": "uint8",
        "shape": (2400, 2400),
        "fill_value": 255,
        "rtol": 0,
        "atol": 0,
    },
    "SNOW": {
        "dtype": "uint8",
        "shape": (2400, 2400),
        "fill_value": 255,
        "rtol": 0,
        "atol": 0,
    },
    "VEG": {
        "dtype": "uint8",
        "shape": (2400, 2400),
        "fill_value": 255,
        "rtol": 0,
        "atol": 0,
    },
}

# Stage 1: raw SCAG bin files (before masking)
RAW_BIN_CONFIGS: dict[str, dict] = {
    "grnsz": {
        "dtype": "uint16",
        "shape": (2400, 2400),
        "fill_value": None,
        "rtol": 0,
        "atol": 0,
    },
    "other": {
        "dtype": "uint8",
        "shape": (2400, 2400),
        "fill_value": None,
        "rtol": 0,
        "atol": 0,
    },
    "rms": {
        "dtype": "uint8",
        "shape": (2400, 2400),
        "fill_value": None,
        "rtol": 0,
        "atol": 0,
    },
    "rock": {
        "dtype": "uint8",
        "shape": (2400, 2400),
        "fill_value": None,
        "rtol": 0,
        "atol": 0,
    },
    "shade": {
        "dtype": "uint8",
        "shape": (2400, 2400),
        "fill_value": None,
        "rtol": 0,
        "atol": 0,
    },
    "snow": {
        "dtype": "uint8",
        "shape": (2400, 2400),
        "fill_value": None,
        "rtol": 0,
        "atol": 0,
    },
    "veg": {
        "dtype": "uint8",
        "shape": (2400, 2400),
        "fill_value": None,
        "rtol": 0,
        "atol": 0,
    },
}

VERSION = "V01.1"


# ---------------------------------------------------------------------------
# Variant builders
# ---------------------------------------------------------------------------


def _masked_variants(tile: str, date: str, product: str) -> list[dict]:
    """VIRSCGDRF_NRT_*.bin.mask / .bin.Unmask variants."""
    prefix, product_id = PRODUCT_TIF_PATTERN[product]
    return [
        {
            "stage": "masked",
            "file_type": ft,
            "masked": masked,
            "tile": tile,
            "filename": f"{prefix}_{ft}_{tile}_{product_id}_{date}_{VERSION}"
            + (".bin.mask" if masked else ".bin.Unmask"),
            "glob": False,
        }
        for ft in MASKED_FILE_CONFIGS
        for masked in (False, True)
    ]


def _raw_bin_variants(tile: str, date: str) -> list[dict]:
    """Raw *.bin variants — filename contains a processing timestamp wildcard."""
    doy = datetime.datetime.strptime(date, "%Y%m%d").strftime("%Y%j")
    return [
        {
            "stage": "raw",
            "file_type": ft,
            "masked": False,
            "tile": tile,
            # processing timestamp is unknown at test-write time, use glob
            "filename": f"VJ109GA_NRT.A{doy}.{tile}.002.*.{ft}.bin",
            "glob": True,
        }
        for ft in RAW_BIN_CONFIGS
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve(directory: Path, variant: dict) -> Path:
    """Resolve a path, handling glob for raw bin files."""
    if variant["glob"]:
        matches = list(directory.glob(variant["filename"]))
        if not matches:
            return directory / variant["filename"]  # non-existent → fixture will skip
        return sorted(matches)[0]
    return directory / variant["filename"]


def _load(path: Path, cfg: dict) -> np.ndarray:
    arr = np.fromfile(path, dtype=cfg["dtype"])
    rows, cols = cfg["shape"]
    if arr.size != rows * cols:
        raise ValueError(
            f"{path.name}: expected {rows * cols} elements, got {arr.size}"
        )
    return arr.reshape(cfg["shape"])


def _valid_mask(arr: np.ndarray, fill_value: Optional[int]) -> np.ndarray:
    mask = np.ones(arr.shape, dtype=bool)
    if fill_value is not None:
        mask &= arr != fill_value
    return mask


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


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _get_cfg(variant: dict) -> dict:
    if variant["stage"] == "masked":
        return MASKED_FILE_CONFIGS[variant["file_type"]]
    return RAW_BIN_CONFIGS[variant["file_type"]]


# ---------------------------------------------------------------------------
# Tiles loader
# ---------------------------------------------------------------------------


def _load_tiles(region: str) -> list[str]:
    tiles_ini = TOPDIR / "src" / "constants" / "tiles.ini"
    if not tiles_ini.exists():
        raise FileNotFoundError(f"tiles.ini not found at {tiles_ini}")
    cfg = configparser.RawConfigParser()
    cfg.optionxform = str  # preserve case
    cfg.read(tiles_ini)
    return ast.literal_eval(cfg.get("TILES", region.upper()))


# ---------------------------------------------------------------------------
# Parametrize
# ---------------------------------------------------------------------------


def pytest_generate_tests(metafunc):
    if "tile_variant" not in metafunc.fixturenames:
        return

    region = metafunc.config.getoption("--region")
    date = metafunc.config.getoption("--date")
    product = metafunc.config.getoption("--product")

    if region is None or date is None:
        metafunc.parametrize("tile_variant", [])
        return

    product = product.upper()
    tiles = _load_tiles(region)

    combos = []
    for tile in tiles:
        combos.extend(_masked_variants(tile, date, product))
        combos.extend(_raw_bin_variants(tile, date))

    ids = [
        f"{c['tile']}_{c['file_type']}_{'masked' if c['masked'] else 'unmasked'}_{c['stage']}"
        for c in combos
    ]

    metafunc.parametrize("tile_variant", combos, ids=ids)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SCAG_GOLDEN_SUBDIR = "scag_regression/golden"


@pytest.fixture()
def golden_file(tile_variant, golden_dir_for):
    directory = golden_dir_for(tile_variant["tile"], subdir=SCAG_GOLDEN_SUBDIR)
    p = _resolve(directory, tile_variant)
    if not p.exists():
        pytest.skip(f"Golden file not found: {p}")
    return p


@pytest.fixture()
def output_file(tile_variant, output_dir_for):
    directory = output_dir_for(tile_variant["tile"])
    p = _resolve(directory, tile_variant)
    if not p.exists():
        pytest.skip(f"Output file not found: {p}")
    return p


@pytest.fixture()
def cfg(tile_variant) -> dict:
    return _get_cfg(tile_variant)


@pytest.fixture()
def arrays(golden_file, output_file, cfg):
    return _load(golden_file, cfg), _load(output_file, cfg)


# ===========================================================================
# Tests
# ===========================================================================


class TestArrayShape:
    """Shape and dtype must always match."""

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


class TestPixelExact:
    """
    Byte-exact pixel comparison.

    SCAG is deterministic Python + binary, so outputs should be
    exactly reproducible across runs on the same machine.
    """

    def test_arrays_equal(self, arrays, cfg):
        golden_arr, output_arr = arrays
        if not np.array_equal(golden_arr, output_arr):
            diff = golden_arr.astype(int) - output_arr.astype(int)
            n_diff = int((diff != 0).sum())
            pytest.fail(
                f"Arrays differ in {n_diff:,} pixels.\n"
                f"  max absolute diff : {np.abs(diff).max()}\n"
                f"  mean absolute diff: {np.abs(diff).mean():.4g}"
            )


class TestValueStatistics:
    """Aggregate statistics as a diagnostic when pixel comparison fails."""

    @pytest.fixture(autouse=True)
    def _compute(self, arrays, cfg):
        golden_arr, output_arr = arrays
        self.g = _stats(golden_arr, cfg["fill_value"])
        self.o = _stats(output_arr, cfg["fill_value"])

    def _assert_equal(self, key: str):
        assert (
            self.o[key] == self.g[key]
        ), f"Statistic '{key}' mismatch: golden={self.g[key]:.6g}, output={self.o[key]:.6g}"

    def test_min(self):
        self._assert_equal("min")

    def test_max(self):
        self._assert_equal("max")

    def test_mean(self):
        self._assert_equal("mean")

    def test_std(self):
        self._assert_equal("std")


class TestMaskedPixelCounts:
    """Valid and fill pixel counts must match exactly."""

    def test_valid_pixel_count(self, arrays, cfg):
        golden_arr, output_arr = arrays
        g = _stats(golden_arr, cfg["fill_value"])
        o = _stats(output_arr, cfg["fill_value"])
        assert o["n_valid"] == g["n_valid"], (
            f"Valid pixel count mismatch: expected {g['n_valid']:,}, got {o['n_valid']:,} "
            f"(diff={abs(o['n_valid'] - g['n_valid']):,})"
        )

    def test_fill_pixel_count(self, arrays, cfg):
        golden_arr, output_arr = arrays
        g = _stats(golden_arr, cfg["fill_value"])
        o = _stats(output_arr, cfg["fill_value"])
        assert o["n_fill"] == g["n_fill"], (
            f"Fill pixel count mismatch: expected {g['n_fill']:,}, got {o['n_fill']:,} "
            f"(diff={abs(o['n_fill'] - g['n_fill']):,})"
        )


class TestByteHash:
    """
    Byte-for-byte MD5 hash.

    Valid for SCAG (unlike DRFS) because the pipeline is deterministic
    Python + binary with no floating-point language differences.
    """

    def test_md5_matches_golden(self, golden_file, output_file):
        golden_hash = _md5(golden_file)
        output_hash = _md5(output_file)
        assert output_hash == golden_hash, (
            f"MD5 mismatch for {output_file.name}\n"
            f"  golden : {golden_hash}\n"
            f"  output : {output_hash}"
        )
