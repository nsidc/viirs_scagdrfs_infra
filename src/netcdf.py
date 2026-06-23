import configparser
import datetime as dt
import os
from pathlib import Path

import netCDF4 as nc
import numpy as np
import rasterio as rs
import yaml

from src.modis_tile_ncattrs import (
    get_geospatial_bounds_latlon,
    get_geotransform,
    get_tiletuple_from_arg,
    get_xy_minmax,
    look_up_latlon_minmax,
)
from src.constants.products import PRODUCT_OUTPUT_PREFIX
from src.constants.paths import TOPDIR

PACKAGE_DIR = Path(__file__).parent
TEMPLATE_DIR = PACKAGE_DIR / "templates"

FILE_PART_TO_VAR = {
    "deltavis": "DRFS_DELTAVIS_PART",
    "drfs_grnsz": "DRFS_DRFSGS_PART",
    "radiative_forcing": "DRFS_RF_PART",
    "grain_size": "SCAG_GS_PART",
    "ice_fraction": "SCAG_ICE_PART",
    "rock_fraction": "SCAG_ROCK_PART",
    "shade_fraction": "SCAG_SHADE_PART",
    "snow_fraction": "SCAG_SNOW_PART",
    "veg_fraction": "SCAG_VEG_PART",
}

VALID_PRODUCTS = ("MOD09GA", "VNP09GA", "VJ109GA")


def _load_yaml_config(config_filename):
    with open(config_filename) as yml_file:
        return yaml.safe_load(yml_file)


def get_crs_info():
    return _load_yaml_config(TEMPLATE_DIR / "crs.yml")


def get_time_var():
    return _load_yaml_config(TEMPLATE_DIR / "time_var.yml")


def get_drfs_vars():
    return _load_yaml_config(TEMPLATE_DIR / "drfs_vars.yml")


def get_scag_vars():
    return _load_yaml_config(TEMPLATE_DIR / "scag_vars.yml")


def get_product_nc_attrs(product: str) -> dict:
    """Return per-product global attribute values from product_nc_attributes.yml.

    Args:
        product: One of 'MOD09GA', 'VNP09GA', 'VJ109GA'.

    Returns:
        Dict of attribute name -> value for the given product.
    """
    if product not in VALID_PRODUCTS:
        raise ValueError(
            f"Unknown product '{product}'. Must be one of {VALID_PRODUCTS}"
        )
    all_attrs = _load_yaml_config(TEMPLATE_DIR / "product_nc_attributes.yml")
    return all_attrs[product]


def get_static_nc_attrs() -> dict:
    """Return static global attributes shared across all products."""
    return _load_yaml_config(TEMPLATE_DIR / "global_attrs.yml")


def get_file_info():
    parser = configparser.ConfigParser(os.environ)
    parser.read(os.path.join(f"{TOPDIR}", "src", "constants", "file_info.ini"))
    return parser


def get_dtype_from_string(type_string):
    match type_string:
        case "S1":
            return "S1"
        case "u1":
            return np.uint8
        case "u2":
            return np.uint16
        case "f4":
            return np.float32
        case "d":
            return np.double
    return np.uint8


def get_dimensions_for_var(var_name, dimensions):
    if var_name == "x":
        return dimensions[1].name
    elif var_name == "y":
        return dimensions[2].name
    elif var_name == "time":
        return dimensions[0].name
    elif var_name == "crs":
        return ()
    else:
        return (dimensions[0].name, dimensions[2].name, dimensions[1].name)


def create_nc_variable(nc_dataset, var_dict, dimensions, masked_tifs, unmasked_tifs):
    for var_name, value in var_dict.items():
        cur_dimensions = get_dimensions_for_var(var_name, dimensions)
        datatype = None
        if "datatype" in value.keys():
            datatype = get_dtype_from_string(value["datatype"])
            del value["datatype"]
        if "_FillValue" in value.keys():
            nc_var = nc_dataset.createVariable(
                var_name,
                datatype,
                cur_dimensions,
                zlib=True,
                fill_value=value["_FillValue"],
            )
            del value["_FillValue"]
        else:
            nc_var = nc_dataset.createVariable(
                var_name, datatype, cur_dimensions, zlib=True, fill_value=None
            )
        for attr, attr_value in value.items():
            if isinstance(attr_value, dict):
                datatype = None
                for key, value in attr_value.items():
                    if key == "datatype":
                        datatype = get_dtype_from_string(value)
                    elif key == "values":
                        attr_value = np.array(value, dtype=datatype)
            nc_var.setncattr(attr, attr_value)
        tif_file = None
        if var_name.startswith("unmasked_") and len(unmasked_tifs) > 0:
            tif_file = str(unmasked_tifs[var_name])
        elif var_name in masked_tifs.keys() and len(masked_tifs) > 0:
            tif_file = str(masked_tifs[var_name])
        if tif_file is not None:
            ds = rs.open(tif_file)
            vardata = ds.read()
            nc_var.set_auto_maskandscale(False)
            nc_var[:] = np.array(vardata[:])
            ds.close()
        elif "data_mask" not in var_name:
            if nc_var.datatype == np.uint8:
                nc_var.set_auto_maskandscale(False)
                no_data_array = np.full((1, 2400, 2400), 255, dtype=nc_var.datatype)
                nc_var[:] = no_data_array[:]
            elif nc_var.datatype == np.uint16:
                nc_var.set_auto_maskandscale(False)
                no_data_array = np.full((1, 2400, 2400), 2550, dtype=nc_var.datatype)
                nc_var[:] = no_data_array[:]


def fill_data_masks(nc_dataset):
    """Set DRFS_data_mask and SCAG_data_mask with flag values from the grain size
    fields or all zeros. The SCAG grain size field is the only field that uses the
    245 flag value. DRFS does not use the 245 flag value at all."""
    scag_data_mask = np.zeros((1, 2400, 2400), dtype=np.uint8)
    drfs_data_mask = np.zeros((1, 2400, 2400), dtype=np.uint8)
    grnsz_var = nc_dataset.variables["grain_size"]
    if grnsz_var:
        vardata = np.array(grnsz_var[:])
        scag_data_mask[vardata > 2000] = vardata[vardata > 2000] / 10
    drfsGS_var = nc_dataset.variables["drfs_grnsz"]
    if drfsGS_var:
        vardata = np.array(drfsGS_var[:])
        drfs_data_mask[vardata > 2000] = vardata[vardata > 2000] / 10
    nc_var = nc_dataset.variables["DRFS_data_mask"]
    nc_var.set_auto_maskandscale(False)
    nc_var[:] = np.array(drfs_data_mask[:])
    nc_var = nc_dataset.variables["SCAG_data_mask"]
    nc_var.set_auto_maskandscale(False)
    nc_var[:] = np.array(scag_data_mask[:])


def find_variable_files(day, tif_dir, tile, file_info, prefix, source_id):
    masked_template = file_info.get("FILE_INFO", "MASKED_TIF_BASENAME", raw=True)
    unmasked_template = file_info.get("FILE_INFO", "UNMASKED_TIF_BASENAME", raw=True)
    masked_var_files = {}
    unmasked_var_files = {}
    for nc_var_name, file_part in FILE_PART_TO_VAR.items():
        masked_filename = masked_template % (
            prefix,
            file_info.get("FILE_INFO", file_part),
            tile,
            source_id,
            day.strftime("%Y%m%d"),
            file_info.get("FILE_INFO", "TIF_VERSIONS"),
        )
        masked_list = list(tif_dir.rglob(masked_filename))
        unmasked_filename = unmasked_template % (
            prefix,
            file_info.get("FILE_INFO", file_part),
            tile,
            source_id,
            day.strftime("%Y%m%d"),
            file_info.get("FILE_INFO", "TIF_VERSIONS"),
        )
        unmasked_list = list(tif_dir.rglob(unmasked_filename))
        if len(masked_list) == 1:
            masked_var_files[nc_var_name] = masked_list[0]
        else:
            print(
                f"Found {len(masked_list)} files instead of the one "
                f"expected file: {masked_filename} in the directory or "
                f"subdirectory of: {tif_dir}"
            )
        if len(unmasked_list) == 1:
            unmasked_var_files["unmasked_" + nc_var_name] = unmasked_list[0]
        else:
            print(
                f"Found {len(unmasked_list)} files instead of the one "
                f"expected file: {unmasked_filename} in the directory or "
                f"subdirectory of: {tif_dir}"
            )
    return masked_var_files, unmasked_var_files


def add_nc_coordinate_values(xmin, xmax, ymin, ymax, nc_dataset):
    """Add coordinate information."""
    ulx, uly = xmin, ymax
    lrx, lry = xmax, ymin

    xdim = nc_dataset.dimensions["y"].size
    xresolution = (lrx - ulx) / xdim
    x_vals = np.linspace(
        ulx + xresolution / 2,
        lrx - xresolution / 2,
        num=xdim,
        dtype=nc_dataset.variables["x"].dtype,
    )
    nc_dataset.variables["x"][:] = x_vals[:]

    ydim = nc_dataset.dimensions["y"].size
    yresolution = (lry - uly) / ydim
    y_vals = np.linspace(
        uly + yresolution / 2,
        lry - yresolution / 2,
        num=ydim,
        dtype=nc_dataset.variables["y"].dtype,
    )
    nc_dataset.variables["y"][:] = y_vals[:]


def add_geospatial_info(tile_id, nc_dataset):
    hid, vid = get_tiletuple_from_arg(tile_id)
    xmin, xmax, ymin, ymax = get_xy_minmax(hid, vid)
    is_valid_tileID, lon_min, lon_max, lat_min, lat_max = look_up_latlon_minmax(
        hid, vid
    )
    geotransform_string = get_geotransform(hid, vid)
    geospatial_bounds_string = get_geospatial_bounds_latlon(hid, vid)

    add_nc_coordinate_values(xmin, xmax, ymin, ymax, nc_dataset)
    nc_dataset.variables["crs"].GeoTransform = geotransform_string
    nc_dataset.geospatial_bounds = geospatial_bounds_string
    nc_dataset.geospatial_lat_min = lat_min
    nc_dataset.geospatial_lat_max = lat_max
    nc_dataset.geospatial_lon_min = lon_min
    nc_dataset.geospatial_lon_max = lon_max


def add_time_info(day, nc_dataset):
    """Set time dimension value and time coverage global attributes."""
    file_time = nc.date2num(
        dt.datetime(year=day.year, month=day.month, day=day.day),
        units=nc_dataset.variables["time"].units,
        calendar=nc_dataset.variables["time"].calendar,
    )
    nc_dataset.variables["time"][0] = file_time

    creation_date_str = dt.date.today().isoformat()
    nc_dataset.date_created = creation_date_str
    nc_dataset.date_modified = creation_date_str

    day_time = dt.datetime(year=day.year, month=day.month, day=day.day)
    nc_dataset.time_coverage_start = day_time.strftime("%Y-%m-%d %H:%M:%S")
    nc_dataset.time_coverage_end = day_time.replace(
        hour=23, minute=59, second=59
    ).strftime("%Y-%m-%d %H:%M:%S")


def create_netcdf(
    day: dt.date, tif_dir: Path, tile_id: str, product: str
) -> nc.Dataset:
    """Create a SCAGDRFS NetCDF file for a given product, tile, and day.

    Args:
        day:     Date to process.
        tif_dir: Directory containing the input TIF files and where the .nc will be written.
        tile_id: MODIS/VIIRS tile identifier (e.g. 'h11v11').
        product: One of 'MOD09GA', 'VNP09GA', 'VJ109GA'.

    Returns:
        The closed nc.Dataset (file has been written to disk).
    """
    if product not in VALID_PRODUCTS:
        raise ValueError(
            f"Unknown product '{product}'. Must be one of {VALID_PRODUCTS}"
        )

    file_info = get_file_info()
    product_attrs = get_product_nc_attrs(product)
    nc_filename = file_info.get("FILE_INFO", "NC_BASENAME", raw=True) % (
        PRODUCT_OUTPUT_PREFIX[product.upper()],
        tile_id,
        product_attrs["source_id"],
        day.strftime("%Y%m%d"),
        product_attrs["nc_filename_version"],
    )
    nc_filepath = Path(os.path.join(tif_dir, nc_filename))
    masked_var_files, unmasked_var_files = find_variable_files(
        day,
        tif_dir,
        tile_id,
        file_info,
        PRODUCT_OUTPUT_PREFIX[product.upper()],
        product_attrs["source_id"],
    )

    # Load attribute sources
    static_attrs = get_static_nc_attrs()
    crs_info = get_crs_info()
    scag_vars = get_scag_vars()
    drfs_vars = get_drfs_vars()
    time_var = get_time_var()

    nc_dataset = nc.Dataset(str(nc_filepath), "w", format="NETCDF4")

    # Apply static global attributes first, then overlay product-specific ones.
    # Skip 'source_id', which is filename-construction metadata, not a NetCDF
    # global attribute in its own right.
    for key, value in static_attrs.items():
        setattr(nc_dataset, key, value)
    for key, value in product_attrs.items():
        if key in ("source_id", "nc_filename_version"):
            continue
        if key == "doi":
            nc_dataset.id = value
            nc_dataset.metadata_link = f"https://doi.org/{value}"
            continue
        setattr(nc_dataset, key, value)

    # Dimensions
    x_dim = nc_dataset.createDimension("x", 2400)
    y_dim = nc_dataset.createDimension("y", 2400)
    time_dim = nc_dataset.createDimension("time", None)
    dimensions = (time_dim, x_dim, y_dim)

    # Coordinate and CRS variables
    create_nc_variable(
        nc_dataset, time_var, dimensions, masked_var_files, unmasked_var_files
    )
    create_nc_variable(
        nc_dataset, crs_info, dimensions, masked_var_files, unmasked_var_files
    )

    # Runtime attributes
    add_geospatial_info(tile_id, nc_dataset)
    add_time_info(day, nc_dataset)
    nc_dataset.software_repository = "https://github.com/nsidc/scagdrfs_infra"
    nc_dataset.software_version_id = (
        open(os.path.join(os.environ["TOPDIR"], "VERSION"), "r").read().rstrip()
    )

    # Science variables
    create_nc_variable(
        nc_dataset, scag_vars, dimensions, masked_var_files, unmasked_var_files
    )
    create_nc_variable(
        nc_dataset, drfs_vars, dimensions, masked_var_files, unmasked_var_files
    )

    fill_data_masks(nc_dataset)
    nc_dataset.close()

    return nc_dataset
