import configparser
import re
import shutil
from pathlib import Path

from src.constants.paths import TOPDIR
from src.util import get_sensor_from_filename


def get_sun_zenith(bip_meta_file):
    metadata = bip_meta_file.read_text()
    sun_zenith_regex = re.compile(r"SUN_ZENITH=(\d*.*\d*)")
    sun_zenith_matches = sun_zenith_regex.search(metadata)
    if sun_zenith_matches is None:
        raise RuntimeError(
            f"Could not parse sun zenith from the BIP metadata file: {bip_meta_file}"
        )
    sun_zenith = float(sun_zenith_matches.group(1))
    return sun_zenith


def get_sza_buckets(bip_meta_file):
    config = configparser.ConfigParser()
    sensor = get_sensor_from_filename(bip_meta_file)
    sza_config = "src/constants/sza_buckets.ini"
    config.read(sza_config)
    sensor_buckets = [
        int(bucket.strip()) for bucket in config.get("sza_buckets", sensor).split(",")
    ]
    return sensor_buckets


def get_zenith_degree(bip_meta_file, sun_zenith):
    sza_buckets = get_sza_buckets(bip_meta_file)
    zenith_degree = sza_buckets[0]
    for index, bucket in enumerate(sza_buckets):
        if bucket != sza_buckets[-1]:
            next_bucket = sza_buckets[index + 1]
        threshold = bucket + ((next_bucket - bucket) / 2)
        zenith_degree = bucket
        if sun_zenith <= threshold:
            break
    return zenith_degree


def copy_spectral_library(sensor, working_dir, zenith_degree):
    # copy files
    scag_config_dir = TOPDIR / "config"
    model_path = scag_config_dir / "scag_models"
    zenith_dir = "z" + str(zenith_degree)
    zenith_path = scag_config_dir / sensor / zenith_dir
    for zenith_file in Path(zenith_path).iterdir():
        shutil.copy(zenith_file, working_dir)
    for model_file in Path(model_path).iterdir():
        shutil.copy(model_file, working_dir)


def copy_scag_ancillary_files(bip_meta_file: Path, output_dir: Path):
    """Copies the ancillary files needed to process a day from the input directory (SCAG
    config directory) to the output directory (working directory).
    """
    sun_zenith = get_sun_zenith(bip_meta_file)
    zenith_degree = get_zenith_degree(bip_meta_file, sun_zenith)
    copy_spectral_library(
        get_sensor_from_filename(bip_meta_file), output_dir, zenith_degree
    )
