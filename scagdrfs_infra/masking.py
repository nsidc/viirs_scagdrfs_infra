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


def cw_mask(bfull_mask, water, data):
    results = []
    for i in np.arange(2400):
        result = map(cloud, bfull_mask[i, :], data[i, :])
        results.append(list(result))
    data_cloud = np.array(results)
    resultsw = []
    for i in np.arange(2400):
        result = map(h2o, water[i, :], data_cloud[i, :])
        resultsw.append(list(result))
    data_cw = np.array(resultsw)
    data_cw = data_cw.astype(np.uint8)
    return data_cw
