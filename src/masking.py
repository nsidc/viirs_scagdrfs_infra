#!/usr/bin/env python

import numpy as np


def cloud(x, y):
    if x:
        return 250
    else:
        return y


def h2o(x, y):
    if x == 100:
        return 235
    else:
        return y


def cloud16(x, y):
    if x:
        return 2500
    else:
        return y


def h2o16(x, y):
    if x == 100:
        return 2350
    else:
        return y


def cw_mask(cloud_mask, water, data):
    # Apply cloud and water masks

    is_cloud = cloud_mask != 0
    is_water = water == 100

    data_cloud_masked = data.copy()
    data_cloud_masked[is_cloud] = 250

    data_cloudwater_masked = data_cloud_masked
    data_cloudwater_masked[is_water] = 235

    return data_cloudwater_masked
