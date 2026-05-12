#!/usr/bin/env python

import datetime as dt
import glob as glob
import os
from pathlib import Path

import numpy as np

# Note: make_tif should be convert_to_geotiff
from src.make_tif import make_tif

# TODO: We should not be pulling scag-routines from drfs-routines
from src.mask_drfs import (
    get_cloud_mask_6band,
    get_file_info_config,
    get_water_mask,
)
from src.masking import cw_mask
from src.constants.field_info import (
    DTYPE_FOR_BITDEPTH,
    FIELD_BITDEPTHS,
    VALID_FIELD_NAMES,
)
from src.constants.products import (
    PRODUCT_FILE_EXTENSION,
    PRODUCT_OUTPUT_PREFIX,
    PRODUCT_SOURCE_ID,
)
from src.util import get_bitdepth_for_field_name, get_field_name


def get_data(filename):
    field_name = get_field_name(filename)
    bitdepth = get_bitdepth_for_field_name(field_name)
    dtype = DTYPE_FOR_BITDEPTH[bitdepth]

    data = np.fromfile(filename, dtype)

    # TODO: This 2400x2400 shape results from choosing 500m resolution
    return data.reshape(2400, 2400)


def write_data(
    output_dir: str,
    var: str,
    tile: str,
    date_str: str,
    mask_status: str,
    actual_var,
    product: str,
):
    prefix = PRODUCT_OUTPUT_PREFIX[product.upper()]
    source_id = PRODUCT_SOURCE_ID[product.upper()]
    filename = (
        "{prefix}_NRT_{var}_{tile}_{source_id}_{date_str}_V01.1.bin."
        "{mask_status}".format(
            prefix=prefix,
            var=var,
            tile=tile,
            source_id=source_id,
            date_str=date_str,
            mask_status=mask_status,
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
    # Note: bip_full_mask only looks at first 6 bands
    cloud_mask = get_cloud_mask_6band(working_dir, src_root, file_info)
    water_mask_data = get_water_mask(file_info, tile)

    scag_bin_files = np.sort(glob.glob(os.path.join(working_dir, "*.bin")))

    bip_meta_file = Path(working_dir) / (
        src_root + file_info.get("FILE_INFO", "BIP_META_SUFFIX")
    )

    # NOTE: This logic is tricky because it looks at both snow and grnsz
    #       and the order that each is modified with flag values matters
    #       ...a LOT.
    print('binary file indices after np.sort()ing:')
    print(f'  grnsz: {scag_bin_files[0]=}')
    print(f'    ice: {scag_bin_files[1]=}')
    print(f' UNUSED: {scag_bin_files[2]=}')
    print(f'   rock: {scag_bin_files[3]=}')
    print(f'  shade: {scag_bin_files[4]=}')
    print(f'   snow: {scag_bin_files[5]=}')
    print(f'    veg: {scag_bin_files[6]=}')

    # TODO: These values should be pulled from configuration, not magic numbers here
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
        working_dir, "SNOW", tile, date.strftime("%Y%m%d"), "Unmask", snow, product
    )
    output_tif = os.path.join(working_dir, filename.replace("bin.Unmask", "Unmask.tif"))
    make_tif(
        meta_file=bip_meta_file,
        input_file=filename,
        depth=bitdepth_str,
        output_file=output_tif,
    )

    snow_cw = cw_mask(cloud_mask, water_mask_data, snow)
    filename = write_data(
        working_dir, "SNOW", tile, date.strftime("%Y%m%d"), "mask", snow_cw, product
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
        working_dir, "GS", tile, date.strftime("%Y%m%d"), "Unmask", grnsz, product
    )
    output_tif = os.path.join(working_dir, filename.replace("bin.Unmask", "Unmask.tif"))
    make_tif(
        meta_file=bip_meta_file,
        input_file=filename,
        depth=bitdepth_str,
        output_file=output_tif,
    )

    grnsz_cw = cw_mask(cloud_mask, water_mask_data, grnsz)
    filename = write_data(
        working_dir, "GS", tile, date.strftime("%Y%m%d"), "mask", grnsz_cw, product
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
    other_cw = cw_mask(cloud_mask, water_mask_data, other)
    filename = write_data(
        working_dir, "ICE", tile, date.strftime("%Y%m%d"), "mask", other_cw, product
    )
    output_tif = os.path.join(working_dir, filename.replace("bin.mask", "tif"))
    make_tif(
        meta_file=bip_meta_file,
        input_file=filename,
        depth=bitdepth_str,
        output_file=output_tif,
    )

    filename = write_data(
        working_dir, "ICE", tile, date.strftime("%Y%m%d"), "Unmask", other, product
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
    rock_cw = cw_mask(cloud_mask, water_mask_data, rock)
    filename = write_data(
        working_dir, "ROCK", tile, date.strftime("%Y%m%d"), "mask", rock_cw, product
    )
    output_tif = os.path.join(working_dir, filename.replace("bin.mask", "tif"))
    make_tif(
        meta_file=bip_meta_file,
        input_file=filename,
        depth=bitdepth_str,
        output_file=output_tif,
    )

    filename = write_data(
        working_dir, "ROCK", tile, date.strftime("%Y%m%d"), "Unmask", rock, product
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
    shade_cw = cw_mask(cloud_mask, water_mask_data, shade)
    filename = write_data(
        working_dir, "SHADE", tile, date.strftime("%Y%m%d"), "mask", shade_cw, product
    )
    output_tif = os.path.join(working_dir, filename.replace("bin.mask", "tif"))
    make_tif(
        meta_file=bip_meta_file,
        input_file=filename,
        depth=bitdepth_str,
        output_file=output_tif,
    )

    filename = write_data(
        working_dir, "SHADE", tile, date.strftime("%Y%m%d"), "Unmask", shade, product
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
    veg_cw = cw_mask(cloud_mask, water_mask_data, veg)
    filename = write_data(
        working_dir, "VEG", tile, date.strftime("%Y%m%d"), "mask", veg_cw, product
    )
    output_tif = os.path.join(working_dir, filename.replace("bin.mask", "tif"))
    make_tif(
        meta_file=bip_meta_file,
        input_file=filename,
        depth=bitdepth_str,
        output_file=output_tif,
    )

    filename = write_data(
        working_dir, "VEG", tile, date.strftime("%Y%m%d"), "Unmask", veg, product
    )
    output_tif = os.path.join(working_dir, filename.replace("bin.Unmask", "Unmask.tif"))
    make_tif(
        meta_file=bip_meta_file,
        input_file=filename,
        depth=bitdepth_str,
        output_file=output_tif,
    )

    return "scag masks completed"
