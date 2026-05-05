"""Unit tests for src/constants and src/util.

These tests require no Alpine filesystem access and can be run anywhere:
    pytest tests/test_constants_and_util.py
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch


# ---------------------------------------------------------------------------
# src/constants/paths.py
# ---------------------------------------------------------------------------


class TestGetNrtDir:
    def test_default_follows_petalib_layout(self):
        from src.constants.paths import get_nrt_dir, PETALIB_DIR

        assert get_nrt_dir("VNP09GA") == PETALIB_DIR / "VNP09GA" / "NRT"
        assert get_nrt_dir("VJ109GA") == PETALIB_DIR / "VJ109GA" / "NRT"
        assert get_nrt_dir("MOD09GA") == PETALIB_DIR / "MOD09GA" / "NRT"

    def test_env_var_override(self, tmp_path):
        with patch.dict(os.environ, {"VNP09GA_NRT_DIR": str(tmp_path)}):
            from src.constants import paths

            result = paths.get_nrt_dir("VNP09GA")
        assert result == tmp_path

    def test_case_insensitive(self):
        from src.constants.paths import get_nrt_dir

        assert get_nrt_dir("vnp09ga") == get_nrt_dir("VNP09GA")

    def test_returns_path_object(self):
        from src.constants.paths import get_nrt_dir

        assert isinstance(get_nrt_dir("MOD09GA"), Path)


class TestGetFinalDir:
    def test_default_follows_petalib_layout(self):
        from src.constants.paths import get_final_dir, PETALIB_DIR

        assert get_final_dir("VJ109GA") == PETALIB_DIR / "VJ109GA" / "FIN"

    def test_env_var_override(self, tmp_path):
        with patch.dict(os.environ, {"VJ109GA_DIR": str(tmp_path)}):
            from src.constants import paths

            result = paths.get_final_dir("VJ109GA")
        assert result == tmp_path

    def test_returns_path_object(self):
        from src.constants.paths import get_final_dir

        assert isinstance(get_final_dir("VJ109GA"), Path)


class TestTopdir:
    def test_topdir_is_repo_root(self):
        """TOPDIR should be three levels above src/constants/paths.py."""
        from src.constants.paths import TOPDIR

        assert (TOPDIR / "src" / "constants" / "paths.py").exists()


# ---------------------------------------------------------------------------
# src/constants/products.py
# ---------------------------------------------------------------------------


class TestProductRegistry:
    def test_supported_products_complete(self):
        from src.constants.products import SUPPORTED_PRODUCTS

        assert set(SUPPORTED_PRODUCTS) == {"MOD09GA", "VNP09GA", "VJ109GA"}

    def test_all_products_have_lance_config(self):
        from src.constants.products import SUPPORTED_PRODUCTS, PRODUCT_LANCE_CONFIG

        for product in SUPPORTED_PRODUCTS:
            assert product in PRODUCT_LANCE_CONFIG
            short_name, concept_id = PRODUCT_LANCE_CONFIG[product]
            assert short_name, f"Missing short_name for {product}"
            assert concept_id, f"Missing concept_id for {product}"

    def test_lance_concept_ids(self):
        from src.constants.products import (
            LANCE_CONCEPT_ID_MOD_NRT,
            LANCE_CONCEPT_ID_VNP_NRT,
            LANCE_CONCEPT_ID_VJ1_NRT,
            LANCE_CONCEPT_ID_VJ1,
        )

        assert LANCE_CONCEPT_ID_MOD_NRT == "C2007661943-LANCEMODIS"
        assert LANCE_CONCEPT_ID_VNP_NRT == "C2780105555-LANCEMODIS"
        assert LANCE_CONCEPT_ID_VJ1_NRT == "C2781246545-LANCEMODIS"
        assert LANCE_CONCEPT_ID_VJ1 == "C2631841524-LPCLOUD"

    def test_product_short_names(self):
        from src.constants.products import (
            PRODUCT_SHORT_NAME_MOD_NRT,
            PRODUCT_SHORT_NAME_VNP_NRT,
            PRODUCT_SHORT_NAME_VJ1_NRT,
            PRODUCT_SHORT_NAME_VJ1,
        )

        assert PRODUCT_SHORT_NAME_MOD_NRT == "MOD09GA_NRT"
        assert PRODUCT_SHORT_NAME_VNP_NRT == "VNP09GA_NRT"
        assert PRODUCT_SHORT_NAME_VJ1_NRT == "VJ109GA_NRT"
        assert PRODUCT_SHORT_NAME_VJ1 == "VJ109GA"

    def test_all_products_have_sensor(self):
        from src.constants.products import SUPPORTED_PRODUCTS, PRODUCT_SENSOR

        for product in SUPPORTED_PRODUCTS:
            assert product in PRODUCT_SENSOR
            assert PRODUCT_SENSOR[product] in ("MODIS", "VIIRS")

    def test_sensor_assignments(self):
        from src.constants.products import PRODUCT_SENSOR

        assert PRODUCT_SENSOR["MOD09GA"] == "MODIS"
        assert PRODUCT_SENSOR["VNP09GA"] == "VIIRS"
        assert PRODUCT_SENSOR["VJ109GA"] == "VIIRS"

    def test_all_products_have_tif_pattern(self):
        from src.constants.products import SUPPORTED_PRODUCTS, PRODUCT_TIF_PATTERN

        for product in SUPPORTED_PRODUCTS:
            assert product in PRODUCT_TIF_PATTERN
            prefix, product_id = PRODUCT_TIF_PATTERN[product]
            assert prefix
            assert product_id

    def test_viirs_tif_patterns_are_distinct(self):
        """VNP09GA and VJ109GA should have different product IDs in TIF patterns."""
        from src.constants.products import PRODUCT_TIF_PATTERN

        _, vnp_id = PRODUCT_TIF_PATTERN["VNP09GA"]
        _, vj1_id = PRODUCT_TIF_PATTERN["VJ109GA"]
        assert vnp_id != vj1_id

    def test_file_extensions(self):
        from src.constants.products import PRODUCT_FILE_EXTENSION

        assert PRODUCT_FILE_EXTENSION["MOD09GA"] == ".hdf"
        assert PRODUCT_FILE_EXTENSION["VNP09GA"] == ".h5"
        assert PRODUCT_FILE_EXTENSION["VJ109GA"] == ".h5"

    def test_all_products_have_file_extension(self):
        from src.constants.products import SUPPORTED_PRODUCTS, PRODUCT_FILE_EXTENSION

        for product in SUPPORTED_PRODUCTS:
            assert product in PRODUCT_FILE_EXTENSION

    def test_final_config_subset_of_supported(self):
        """Final products must be a subset of supported products."""
        from src.constants.products import (
            SUPPORTED_PRODUCTS,
            PRODUCT_LANCE_CONFIG_FINAL,
        )

        for product in PRODUCT_LANCE_CONFIG_FINAL:
            assert product in SUPPORTED_PRODUCTS


# ---------------------------------------------------------------------------
# src/util.py — filename parsing
# ---------------------------------------------------------------------------


class TestGetSensorFromFilename:
    def test_modis_filename(self):
        from src.util import get_sensor_from_filename

        assert (
            get_sensor_from_filename("MOD09GA.A2026042.h09v05.061.2026043.hdf")
            == "MODIS"
        )

    def test_vnp_filename(self):
        from src.util import get_sensor_from_filename

        assert get_sensor_from_filename("VNP09GA_NRT.A2026042.h09v05.002.h5") == "VIIRS"

    def test_vj1_filename(self):
        from src.util import get_sensor_from_filename

        assert get_sensor_from_filename("VJ109GA_NRT.A2026042.h09v05.002.h5") == "VIIRS"

    def test_unknown_filename_raises(self):
        from src.util import get_sensor_from_filename

        with pytest.raises(RuntimeError, match="Cannot determine sensor"):
            get_sensor_from_filename("UNKNOWN.A2026042.h09v05.bin")


class TestGetFieldName:
    # Underscore-heavy MODIS-style: field is at index 2
    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("MODSCGDRF_NRT_GS_h08v04_MOD09GANRT061_20250331_V01.1.bin.mask", "GS"),
            (
                "MODSCGDRF_NRT_DELTAVIS_h08v04_MOD09GANRT061_20250331_V01.1.bin.mask",
                "DELTAVIS",
            ),
            ("MODSCGDRF_NRT_RF_h08v04_MOD09GANRT061_20250331_V01.1.bin.mask", "RF"),
        ],
    )
    def test_modis_style_filenames(self, filename, expected):
        from src.util import get_field_name

        assert get_field_name(filename) == expected

    # Dot-heavy VIIRS-style: field is at index 6
    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("VNP09GA_NRT.A2026042.h30v13.002.2026043041826.grnsz.bin", "grnsz"),
            ("VNP09GA_NRT.A2026042.h30v13.002.2026043041826.deltavis.bin", "deltavis"),
            ("VNP09GA_NRT.A2026042.h30v13.002.2026043041826.forcing.bin", "forcing"),
        ],
    )
    def test_viirs_style_filenames(self, filename, expected):
        from src.util import get_field_name

        assert get_field_name(filename) == expected

    def test_accepts_path_object(self):
        from src.util import get_field_name

        p = Path("MODSCGDRF_NRT_GS_h08v04_MOD09GANRT061_20250331_V01.1.bin.mask")
        assert get_field_name(p) == "GS"

    def test_invalid_type_raises(self):
        from src.util import get_field_name

        with pytest.raises(RuntimeError):
            get_field_name(12345)


class TestGetDateFromFilename:
    def test_parses_doy_correctly(self):
        from src.util import get_date_from_filename
        import datetime as dt

        result = get_date_from_filename("MOD09GA.A2026042.h09v05.hdf")
        assert result == dt.datetime(2026, 2, 11)  # day 42 of 2026

    def test_missing_date_raises(self):
        from src.util import get_date_from_filename

        with pytest.raises(RuntimeError, match="Cannot determine date"):
            get_date_from_filename("no_date_here.bin")


class TestGetTileIdFromFilename:
    def test_parses_tile(self):
        from src.util import get_tile_id_from_filename

        assert get_tile_id_from_filename("MOD09GA.A2026042.h09v05.061.hdf") == "h09v05"

    def test_two_digit_tile(self):
        from src.util import get_tile_id_from_filename

        assert (
            get_tile_id_from_filename("VNP09GA_NRT.A2026042.h30v13.002.h5") == "h30v13"
        )

    def test_missing_tile_raises(self):
        from src.util import get_tile_id_from_filename

        with pytest.raises(RuntimeError, match="Cannot determine tile"):
            get_tile_id_from_filename("no_tile_here.bin")


class TestGetBitdepthForFieldName:
    @pytest.mark.parametrize(
        "field,expected",
        [
            ("grnsz", 16),
            ("GS", 16),
            ("drfsGS", 16),
            ("RF", 16),
            ("DELTAVIS", 8),
            ("ICE", 8),
            ("ROCK", 8),
            ("SHADE", 8),
            ("SNOW", 8),
            ("VEG", 8),
            ("other", 8),
            ("rms", 8),
            ("rock", 8),
            ("shade", 8),
            ("snow", 8),
            ("veg", 8),
        ],
    )
    def test_known_fields(self, field, expected):
        from src.util import get_bitdepth_for_field_name

        assert get_bitdepth_for_field_name(field) == expected

    def test_unknown_field_raises(self):
        from src.util import get_bitdepth_for_field_name

        with pytest.raises(RuntimeError, match="no defined bitdepth"):
            get_bitdepth_for_field_name("not_a_real_field")


# ---------------------------------------------------------------------------
# src/util.py — date helpers
# ---------------------------------------------------------------------------


class TestDateRange:
    def test_single_day(self):
        from src.util import date_range
        import datetime as dt

        result = list(
            date_range(
                start_date=dt.date(2026, 3, 1),
                end_date=dt.date(2026, 3, 1),
            )
        )
        assert len(result) == 1
        assert result[0] == dt.date(2026, 3, 1)

    def test_inclusive_range(self):
        from src.util import date_range
        import datetime as dt

        result = list(
            date_range(
                start_date=dt.date(2026, 3, 1),
                end_date=dt.date(2026, 3, 5),
            )
        )
        assert len(result) == 5
        assert result[-1] == dt.date(2026, 3, 5)

    def test_returns_dates_not_datetimes(self):
        from src.util import date_range
        import datetime as dt

        for d in date_range(
            start_date=dt.date(2026, 1, 1), end_date=dt.date(2026, 1, 3)
        ):
            assert isinstance(d, dt.date)
            assert not isinstance(d, dt.datetime)
