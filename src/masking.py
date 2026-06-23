import numpy as np


def calc_cloud_mask(cloud_data):
    # Return boolean cloud mask
    # Should this be a configurable flag value (or range)?
    return cloud_data != 0


def calc_water_mask(water_data):
    # Return boolean water mask
    # Should this be a configurable flag value?
    return water_data == 100


def cw_mask(cloud_data, water_data, data):
    # Apply cloud and water masks

    # TODO: These values should be moved to a configuration file
    if data.dtype == np.uint8:
        cloud_flagval = 250
        water_flagval = 235
    elif data.dtype == np.uint16:
        cloud_flagval = 2500
        water_flagval = 2350
    else:
        raise ValueError(f"Cannot determine flag values for data type: {data.dtype}")

    is_cloud = calc_cloud_mask(cloud_data)
    is_water = calc_water_mask(water_data)

    data_cloud_masked = data.copy()
    data_cloud_masked[is_cloud] = cloud_flagval

    data_cloudwater_masked = data_cloud_masked
    data_cloudwater_masked[is_water] = water_flagval

    return data_cloudwater_masked
