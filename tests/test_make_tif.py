import numpy as np
import pytest
from pathlib import Path
from unittest.mock import patch
from osgeo import gdal, osr

from src.make_tif import make_tif


MODIS_PROJ = "+proj=sinu +R=6371007.181 +nadgrids=@null +wktext"

BASE_BIP_INFO = {
    "num_samples": "10",
    "num_lines": "8",
    "proj_string": MODIS_PROJ,
    "ul_corner_x": "-1000.0",
    "ul_corner_y": "2000.0",
    "lr_corner_x": "0.0",
    "lr_corner_y": "1000.0",
}


def make_raw_file(
    path: Path, num_samples: int, num_lines: int, dtype: np.dtype
) -> np.ndarray:
    """Write a raw binary grayscale file and return the array that was written."""
    rng = np.random.default_rng(42)
    if dtype == np.uint8:
        data = rng.integers(0, 200, size=(num_lines, num_samples), dtype=dtype)
    else:
        data = rng.integers(0, 2000, size=(num_lines, num_samples), dtype=dtype)
    path.write_bytes(data.tobytes())
    return data


@pytest.fixture
def bip_info():
    return BASE_BIP_INFO.copy()


@pytest.fixture
def tmp_input_16(tmp_path) -> tuple[Path, np.ndarray]:
    f = tmp_path / "input.img"
    data = make_raw_file(f, num_samples=10, num_lines=8, dtype=np.uint16)
    return f, data


@pytest.fixture
def tmp_input_8(tmp_path) -> tuple[Path, np.ndarray]:
    f = tmp_path / "input.img"
    data = make_raw_file(f, num_samples=10, num_lines=8, dtype=np.uint8)
    return f, data


# ── helpers ──────────────────────────────────────────────────────────────────


def open_output(path: Path):
    ds = gdal.Open(str(path))
    assert ds is not None, f"GDAL could not open {path}"
    return ds


# ── tests ─────────────────────────────────────────────────────────────────────


class TestMakeTif16Bit:
    def test_creates_output_file(self, tmp_path, bip_info, tmp_input_16):
        input_file, _ = tmp_input_16
        output_file = tmp_path / "out.tif"
        with patch("src.make_tif.get_info_from_bip_file", return_value=bip_info):
            make_tif(Path("dummy.meta"), input_file, "16", output_file)
        assert output_file.exists()

    def test_nodata_is_2550(self, tmp_path, bip_info, tmp_input_16):
        input_file, _ = tmp_input_16
        output_file = tmp_path / "out.tif"
        with patch("src.make_tif.get_info_from_bip_file", return_value=bip_info):
            make_tif(Path("dummy.meta"), input_file, "16", output_file)
        ds = open_output(output_file)
        assert ds.GetRasterBand(1).GetNoDataValue() == 2550

    def test_dtype_is_uint16(self, tmp_path, bip_info, tmp_input_16):
        input_file, _ = tmp_input_16
        output_file = tmp_path / "out.tif"
        with patch("src.make_tif.get_info_from_bip_file", return_value=bip_info):
            make_tif(Path("dummy.meta"), input_file, "16", output_file)
        ds = open_output(output_file)
        assert ds.GetRasterBand(1).DataType == gdal.GDT_UInt16

    def test_pixel_values_roundtrip(self, tmp_path, bip_info, tmp_input_16):
        input_file, original = tmp_input_16
        output_file = tmp_path / "out.tif"
        with patch("src.make_tif.get_info_from_bip_file", return_value=bip_info):
            make_tif(Path("dummy.meta"), input_file, "16", output_file)
        ds = open_output(output_file)
        result = ds.GetRasterBand(1).ReadAsArray()
        np.testing.assert_array_equal(result, original)


class TestMakeTif8Bit:
    def test_nodata_is_255(self, tmp_path, bip_info, tmp_input_8):
        input_file, _ = tmp_input_8
        output_file = tmp_path / "out.tif"
        with patch("src.make_tif.get_info_from_bip_file", return_value=bip_info):
            make_tif(Path("dummy.meta"), input_file, "8", output_file)
        ds = open_output(output_file)
        assert ds.GetRasterBand(1).GetNoDataValue() == 255

    def test_dtype_is_byte(self, tmp_path, bip_info, tmp_input_8):
        input_file, _ = tmp_input_8
        output_file = tmp_path / "out.tif"
        with patch("src.make_tif.get_info_from_bip_file", return_value=bip_info):
            make_tif(Path("dummy.meta"), input_file, "8", output_file)
        ds = open_output(output_file)
        assert ds.GetRasterBand(1).DataType == gdal.GDT_Byte

    def test_pixel_values_roundtrip(self, tmp_path, bip_info, tmp_input_8):
        input_file, original = tmp_input_8
        output_file = tmp_path / "out.tif"
        with patch("src.make_tif.get_info_from_bip_file", return_value=bip_info):
            make_tif(Path("dummy.meta"), input_file, "8", output_file)
        ds = open_output(output_file)
        result = ds.GetRasterBand(1).ReadAsArray()
        np.testing.assert_array_equal(result, original)


class TestGeotransform:
    def test_geotransform_values(self, tmp_path, bip_info, tmp_input_16):
        """pixel_width = (lr_x - ul_x) / num_samples, pixel_height = (lr_y - ul_y) / num_lines"""
        input_file, _ = tmp_input_16
        output_file = tmp_path / "out.tif"
        with patch("src.make_tif.get_info_from_bip_file", return_value=bip_info):
            make_tif(Path("dummy.meta"), input_file, "16", output_file)

        ds = open_output(output_file)
        gt = ds.GetGeoTransform()

        expected_pixel_width = (0.0 - (-1000.0)) / 10  # 100.0
        expected_pixel_height = (1000.0 - 2000.0) / 8  # -125.0

        assert gt[0] == pytest.approx(-1000.0)  # ul_x
        assert gt[3] == pytest.approx(2000.0)  # ul_y
        assert gt[1] == pytest.approx(expected_pixel_width)
        assert gt[5] == pytest.approx(expected_pixel_height)
        assert gt[2] == pytest.approx(0.0)  # no rotation
        assert gt[4] == pytest.approx(0.0)


class TestProjection:
    def test_projection_is_sinusoidal(self, tmp_path, bip_info, tmp_input_16):
        input_file, _ = tmp_input_16
        output_file = tmp_path / "out.tif"
        with patch("src.make_tif.get_info_from_bip_file", return_value=bip_info):
            make_tif(Path("dummy.meta"), input_file, "16", output_file)

        ds = open_output(output_file)
        srs = osr.SpatialReference(wkt=ds.GetProjection())
        assert srs.GetAttrValue("PROJECTION") == "Sinusoidal"

    def test_projection_sphere_radius(self, tmp_path, bip_info, tmp_input_16):
        input_file, _ = tmp_input_16
        output_file = tmp_path / "out.tif"
        with patch("src.make_tif.get_info_from_bip_file", return_value=bip_info):
            make_tif(Path("dummy.meta"), input_file, "16", output_file)

        ds = open_output(output_file)
        srs = osr.SpatialReference(wkt=ds.GetProjection())
        assert srs.GetSemiMajor() == pytest.approx(6371007.181, rel=1e-6)


class TestOutputDimensions:
    def test_raster_size(self, tmp_path, bip_info, tmp_input_16):
        input_file, _ = tmp_input_16
        output_file = tmp_path / "out.tif"
        with patch("src.make_tif.get_info_from_bip_file", return_value=bip_info):
            make_tif(Path("dummy.meta"), input_file, "16", output_file)

        ds = open_output(output_file)
        assert ds.RasterXSize == 10
        assert ds.RasterYSize == 8
        assert ds.RasterCount == 1
