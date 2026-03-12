#!/usr/bin/env python

import datetime as dt
import glob as glob
import os
from pathlib import Path

import numpy as np

from src.make_tif import make_tif
from src.mask_drfs import (
    cw_mask16,
    get_bip_full_mask,
    get_file_info_config,
    get_water_mask,
)
from src.masking import cw_mask
from src.constants.field_info import (
    DTYPE_FOR_BITDEPTH,
    FIELD_BITDEPTHS,
    VALID_FIELD_NAMES,
)
from src.constants.products import PRODUCT_FILE_EXTENSION, PRODUCT_OUTPUT_PREFIX, PRODUCT_SOURCE_ID
from src.util import get_bitdepth_for_field_name, get_field_name


def get_data(filename):
    field_name = get_field_name(filename)
    bitdepth = get_bitdepth_for_field_name(field_name)
    dtype = DTYPE_FOR_BITDEPTH[bitdepth]

    # with open(filename, "rb") as f:
    #    dtype = kkk
    #    if "grnsz" in filename:
    #        data = np.fromfile(f, dtype=np.uint16)
    #    else:
    #        data = np.fromfile(f, dtype=np.uint8)
    data = np.fromfile(filename, dtype)

    return data.reshape(2400, 2400)


def write_data(
    output_dir: str, var: str, tile: str, date_str: str, mask_status: str, actual_var
):
    prefix = PRODUCT_OUTPUT_PREFIX[product.upper()]
    source_id = PRODUCT_SOURCE_ID[product.upper()]
    filename = (
        "{prefix}_NRT_{var}_{tile}_{source_id)_{date_str}_V01.1.bin."
        "{mask_status}".format(
            var=var, tile=tile, date_str=date_str, mask_status=mask_status
        )
    )
    outfile_path = os.path.join(output_dir, filename)
    with open(outfile_path, "wb") as output_file:
        output_file.write(actual_var)
    return outfile_path


def mask_scag(date: dt.date, working_dir: Path, tile: str, product: str):
    ext = PRODUCT_FILE_EXTENSION[product.upper()]

    src_files = list(working_dir.glob(f"**/*{ext}"))
    if len(src_files) != 1:
        print(
            "Found either zero or multiple HDF files in working directory: "
            + str(working_dir)
        )
    src_file = src_files[0]

    file_info = get_file_info_config()
    src_root = src_file.stem
    bip_full_mask = get_bip_full_mask(working_dir, src_root, file_info)
    water_mask_data = get_water_mask(file_info, tile)

    scag_bin_files = np.sort(glob.glob(os.path.join(working_dir, "*.bin")))

    bip_meta_file = Path(working_dir) / (
        src_root + file_info.get("FILE_INFO", "BIP_META_SUFFIX")
    )

    # NOTE: This logic is tricky because it looks at both snow and grnsz
    #       and the order that each is modified with flag values matters
    #       ...a LOT.
    grnsz = get_data(scag_bin_files[0])
    snow = get_data(scag_bin_files[5])
    snow[snow < 15] = 0
    grnsz[snow < 15] = 2450
    snow[grnsz == 0] = 255
    grnsz[grnsz == 0] = 2550
    grnsz[grnsz == 65535] = 2550

    # Make SNOW geotiffs
    bitdepth_str = str(FIELD_BITDEPTHS["SNOW"])

    filename = write_data(
        working_dir, "SNOW", tile, date.strftime("%Y%m%d"), "Unmask", snow
    )
    output_tif = os.path.join(working_dir, filename.replace("bin.Unmask", "Unmask.tif"))
    make_tif(
        meta_file=bip_meta_file,
        input_file=filename,
        depth=bitdepth_str,
        output_file=output_tif,
    )

    snow_cw = cw_mask(bip_full_mask, water_mask_data, snow)
    filename = write_data(
        working_dir, "SNOW", tile, date.strftime("%Y%m%d"), "mask", snow_cw
    )
    output_tif = os.path.join(working_dir, filename.replace("bin.mask", "tif"))
    make_tif(
        meta_file=bip_meta_file,
        input_file=filename,
        depth=bitdepth_str,
        output_file=output_tif,
    )

    # Make grainsize GS  geotiffs
    bitdepth_str = str(FIELD_BITDEPTHS["GS"])

    filename = write_data(
        working_dir, "GS", tile, date.strftime("%Y%m%d"), "Unmask", grnsz
    )
    output_tif = os.path.join(working_dir, filename.replace("bin.Unmask", "Unmask.tif"))
    make_tif(
        meta_file=bip_meta_file,
        input_file=filename,
        depth=bitdepth_str,
        output_file=output_tif,
    )

    grnsz_cw = cw_mask16(bip_full_mask, water_mask_data, grnsz)
    filename = write_data(
        working_dir, "GS", tile, date.strftime("%Y%m%d"), "mask", grnsz_cw
    )
    output_tif = os.path.join(working_dir, filename.replace("bin.mask", "tif"))
    make_tif(
        meta_file=bip_meta_file,
        input_file=filename,
        depth=bitdepth_str,
        output_file=output_tif,
    )

    # Make ICE geotiffs
    bitdepth_str = str(FIELD_BITDEPTHS["ICE"])

    other = get_data(scag_bin_files[1])
    other[other < 15] = 0
    other_cw = cw_mask(bip_full_mask, water_mask_data, other)
    filename = write_data(
        working_dir, "ICE", tile, date.strftime("%Y%m%d"), "mask", other_cw
    )
    output_tif = os.path.join(working_dir, filename.replace("bin.mask", "tif"))
    make_tif(
        meta_file=bip_meta_file,
        input_file=filename,
        depth=bitdepth_str,
        output_file=output_tif,
    )

    filename = write_data(
        working_dir, "ICE", tile, date.strftime("%Y%m%d"), "Unmask", other
    )
    output_tif = os.path.join(working_dir, filename.replace("bin.Unmask", "Unmask.tif"))
    make_tif(
        meta_file=bip_meta_file,
        input_file=filename,
        depth=bitdepth_str,
        output_file=output_tif,
    )

    # Make ROCK geotiffs
    bitdepth_str = str(FIELD_BITDEPTHS["ROCK"])

    rock = get_data(scag_bin_files[3])
    rock[rock < 15] = 0
    rock_cw = cw_mask(bip_full_mask, water_mask_data, rock)
    filename = write_data(
        working_dir, "ROCK", tile, date.strftime("%Y%m%d"), "mask", rock_cw
    )
    output_tif = os.path.join(working_dir, filename.replace("bin.mask", "tif"))
    make_tif(
        meta_file=bip_meta_file,
        input_file=filename,
        depth=bitdepth_str,
        output_file=output_tif,
    )

    filename = write_data(
        working_dir, "ROCK", tile, date.strftime("%Y%m%d"), "Unmask", rock
    )
    output_tif = os.path.join(working_dir, filename.replace("bin.Unmask", "Unmask.tif"))
    make_tif(
        meta_file=bip_meta_file,
        input_file=filename,
        depth=bitdepth_str,
        output_file=output_tif,
    )

    # Make SHADE geotiffs
    bitdepth_str = str(FIELD_BITDEPTHS["SHADE"])

    shade = get_data(scag_bin_files[4])
    shade[shade < 15] = 0
    shade_cw = cw_mask(bip_full_mask, water_mask_data, shade)
    filename = write_data(
        working_dir, "SHADE", tile, date.strftime("%Y%m%d"), "mask", shade_cw
    )
    output_tif = os.path.join(working_dir, filename.replace("bin.mask", "tif"))
    make_tif(
        meta_file=bip_meta_file,
        input_file=filename,
        depth=bitdepth_str,
        output_file=output_tif,
    )

    filename = write_data(
        working_dir, "SHADE", tile, date.strftime("%Y%m%d"), "Unmask", shade
    )
    output_tif = os.path.join(working_dir, filename.replace("bin.Unmask", "Unmask.tif"))
    make_tif(
        meta_file=bip_meta_file,
        input_file=filename,
        depth=bitdepth_str,
        output_file=output_tif,
    )

    # Make VEG geotiffs
    bitdepth_str = str(FIELD_BITDEPTHS["VEG"])

    veg = get_data(scag_bin_files[6])
    veg[veg < 15] = 0
    veg_cw = cw_mask(bip_full_mask, water_mask_data, veg)
    filename = write_data(
        working_dir, "VEG", tile, date.strftime("%Y%m%d"), "mask", veg_cw
    )
    output_tif = os.path.join(working_dir, filename.replace("bin.mask", "tif"))
    make_tif(
        meta_file=bip_meta_file,
        input_file=filename,
        depth=bitdepth_str,
        output_file=output_tif,
    )

    filename = write_data(
        working_dir, "VEG", tile, date.strftime("%Y%m%d"), "Unmask", veg
    )
    output_tif = os.path.join(working_dir, filename.replace("bin.Unmask", "Unmask.tif"))
    make_tif(
        meta_file=bip_meta_file,
        input_file=filename,
        depth=bitdepth_str,
        output_file=output_tif,
    )

    return "scag masks completed"
