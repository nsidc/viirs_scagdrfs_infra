"""
Pytest configuration and fixtures for regression tests.

Golden files are expected at:
    PETALIB_DIR/drfs_regression/golden/<tile>/

Output files are expected at:
    WORK_DIR/<product>/<YYYY.MM.DD>/<tile>/

Run unit tests without any flags:
    pytest tests/

Run regression tests with required flags:
    pytest tests/ -v --date 20260309 --region onetile --product MOD09GA
"""

import ast
import configparser
import pytest
from pathlib import Path

from src.constants.paths import PETALIB_DIR, WORK_DIR, TOPDIR

_PETALIB_DIR = PETALIB_DIR
_WORK_DIR = WORK_DIR

# tiles.ini lives under src/constants/ — one level up from tests/
_TILES_INI = TOPDIR / "src" / "constants" / "tiles.ini"


def _load_tiles(region: str) -> list[str]:
    """Read tile list for a region from tiles.ini, preserving key case."""
    if not _TILES_INI.exists():
        raise FileNotFoundError(f"tiles.ini not found at {_TILES_INI}")
    cfg = configparser.RawConfigParser()
    cfg.optionxform = str  # preserve case so ONETILE matches
    cfg.read(_TILES_INI)
    key = region.upper()
    if not cfg.has_option("TILES", key):
        available = list(cfg.options("TILES"))
        raise ValueError(
            f"Region '{region}' not found in tiles.ini. "
            f"Available regions: {', '.join(available)}"
        )
    return ast.literal_eval(cfg.get("TILES", key))


def pytest_addoption(parser):
    parser.addoption(
        "--date",
        default=None,
        help="Processing date (YYYYMMDD), e.g. 20260309",
    )
    parser.addoption(
        "--region",
        default=None,
        help="Region name from tiles.ini, e.g. onetile, western_us",
    )
    parser.addoption(
        "--product",
        default="MOD09GA",
        help="Product name (MOD09GA, VNP09GA, VJ109GA)",
    )


@pytest.fixture(scope="session")
def date(request) -> str:
    val = request.config.getoption("--date")
    if val is None:
        pytest.skip("--date not provided (regression tests only)")
    return val


@pytest.fixture(scope="session")
def region(request) -> str:
    val = request.config.getoption("--region")
    if val is None:
        pytest.skip("--region not provided (regression tests only)")
    return val


@pytest.fixture(scope="session")
def product(request) -> str:
    return request.config.getoption("--product").upper()


@pytest.fixture(scope="session")
def tiles(region) -> list[str]:
    return _load_tiles(region)


@pytest.fixture()
def golden_dir_for():
    def _get(tile: str, subdir: str = "drfs_regression/golden") -> Path:
        path = _PETALIB_DIR / subdir / tile
        if not path.exists():
            pytest.skip(f"Golden directory not found: {path}")
        return path

    return _get


@pytest.fixture()
def output_dir_for(date, product):
    """Returns a callable: tile -> output Path."""

    def _get(tile: str) -> Path:
        date_dotted = f"{date[:4]}.{date[4:6]}.{date[6:]}"
        path = _WORK_DIR / product / date_dotted / tile
        if not path.exists():
            pytest.skip(f"Output directory not found: {path}")
        return path

    return _get
