"""Information common to SCAG/DRFS runs at NSIDC"""

import numpy as np

VALID_FIELD_NAMES = (
    # .mask and .Unmask file names
    "DELTAVIS",
    "drfsGS",
    "GS",
    "ICE",
    "RF",
    "ROCK",
    "SHADE",
    "SNOW",
    "VEG",
    # .bin file names
    "grnsz",
    "other",
    "rms",
    "rock",
    "shade",
    "snow",
    "veg",
)

FIELD_BITDEPTHS = {
    "DELTAVIS": 8,
    "drfsGS": 16,
    "GS": 16,
    "ICE": 8,
    "RF": 16,
    "ROCK": 8,
    "SHADE": 8,
    "SNOW": 8,
    "VEG": 8,
    "grnsz": 16,
    "other": 8,
    "rms": 8,
    "rock": 8,
    "shade": 8,
    "snow": 8,
    "veg": 8,
}

DTYPE_FOR_BITDEPTH = {
    8: np.uint8,
    16: np.uint16,
}
