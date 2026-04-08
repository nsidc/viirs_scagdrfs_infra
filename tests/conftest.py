"""
Pytest configuration and fixtures for DRFS binary regression tests.

Requires environment variables set in env.sh:
    PETALIB_DIR   e.g. /pl/active/daac-production
    WORK_DIR   e.g. /scratch/alpine/roma8902/scagdrfs/working

Tile lists are read from scagdrfs_infra/constants/tiles.ini in the repo root.

Golden files are expected at:
    $PETALIB_DIR/drfs_regression/golden/<tile>/

Output files are expected at:
    $WORK_DIR/<YYYY.MM.DD>/<tile>/

Run with:
    pytest tests/drfs_regression/ -v --date 20260309 --region onetile
"""

import ast
import os
import configparser
import pytest
from pathlib import Path

_PETALIB_DIR = os.environ.get("PETALIB_DIR")
_WORK_DIR = os.environ.get("WORK_DIR")

# tiles.ini lives at the repo root — two levels up from tests/drfs_regression/
_TILES_INI = Path(__file__).parents[2] / "scagdrfs_infra" / "constants" / "tiles.ini"


def _load_tiles(region: str) -> list[str]:
    """Read tile list for a region from tiles.ini."""
    if not _TILES_INI.exists():
        raise FileNotFoundError(f"tiles.ini not found at {_TILES_INI}")
    cfg = configparser.ConfigParser()
    cfg.read(_TILES_INI)
    key = region.upper()
    if not cfg.has_option("TILES", key):
        available = [k.lower() for k in cfg.options("TILES")]
        raise ValueError(
            f"Region '{region}' not found in tiles.ini. "
            f"Available regions: {', '.join(available)}"
        )
    return ast.literal_eval(cfg.get("TILES", key))


def pytest_addoption(parser):
    parser.addoption(
        "--date",
        required=True,
        help="Processing date (YYYYMMDD), e.g. 20260309",
    )
    parser.addoption(
        "--region",
        required=True,
        help="Region name from tiles.ini, e.g. onetile, western_us",
    )


@pytest.fixture(scope="session")
def date(request) -> str:
    return request.config.getoption("--date")


@pytest.fixture(scope="session")
def region(request) -> str:
    return request.config.getoption("--region")


@pytest.fixture(scope="session")
def tiles(region) -> list[str]:
    return _load_tiles(region)


@pytest.fixture(scope="session")
def golden_dir_for(tiles):
    """Returns a callable: tile -> golden Path."""

    def _get(tile: str) -> Path:
        if not _PETALIB_DIR:
            pytest.skip("PETALIB_DIR environment variable is not set")
        path = Path(_PETALIB_DIR) / "drfs_regression" / "golden" / tile
        if not path.exists():
            pytest.skip(f"Golden directory not found: {path}")
        return path

    return _get


@pytest.fixture(scope="session")
def output_dir_for(date, tiles):
    """Returns a callable: tile -> output Path."""

    def _get(tile: str) -> Path:
        if not _WORK_DIR:
            pytest.skip("WORK_DIR environment variable is not set")
        date_dotted = f"{date[:4]}.{date[4:6]}.{date[6:]}"
        path = Path(_WORK_DIR) / date_dotted / tile
        if not path.exists():
            pytest.skip(f"Output directory not found: {path}")
        return path

    return _get
