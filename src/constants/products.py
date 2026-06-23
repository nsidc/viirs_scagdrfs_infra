"""VIIRS product configuration."""

import os


# Concept IDs for different VIIRS products
# TODO: Is there also a non-NRT concept-id for each of these?
# RM NOTE: The concept-id is definitely different for not NRT.
LANCE_CONCEPT_ID_MOD_NRT = "C2007661943-LANCEMODIS"  # MOD09GA NRT
LANCE_CONCEPT_ID_VNP_NRT = "C2780105555-LANCEMODIS"  # VNP09GA (NPP) NRT
LANCE_CONCEPT_ID_VJ1_NRT = "C2781246545-LANCEMODIS"  # VJ109GA (NOAA-20) NRT
LANCE_CONCEPT_ID_VJ1 = "C2631841524-LPCLOUD"  # VJ109GA (non-NRT product)

# Product short names
PRODUCT_SHORT_NAME_VNP_NRT = "VNP09GA_NRT"
PRODUCT_SHORT_NAME_VJ1_NRT = "VJ109GA_NRT"
PRODUCT_SHORT_NAME_VJ1 = "VJ109GA"
PRODUCT_SHORT_NAME_MOD_NRT = "MOD09GA_NRT"

PRODUCT_LANCE_CONFIG = {
    "MOD09GA": (PRODUCT_SHORT_NAME_MOD_NRT, LANCE_CONCEPT_ID_MOD_NRT),
    "VNP09GA": (PRODUCT_SHORT_NAME_VNP_NRT, LANCE_CONCEPT_ID_VNP_NRT),
    "VJ109GA": (PRODUCT_SHORT_NAME_VJ1_NRT, LANCE_CONCEPT_ID_VJ1_NRT),
}

PRODUCT_LANCE_CONFIG_FINAL = {
    "VJ109GA": (PRODUCT_SHORT_NAME_VJ1, LANCE_CONCEPT_ID_VJ1),
    # MOD09GA and VNP09GA final concept IDs to be added when needed
}

PRODUCT_SENSOR = {
    "MOD09GA": "MODIS",
    "VNP09GA": "VIIRS",
    "VJ109GA": "VIIRS",
}

# (output_prefix, product_id) used in TIF filename glob patterns
PRODUCT_TIF_PATTERN = {
    "MOD09GA": ("MODSCGDRF_NRT", "MOD09GANRT061"),
    "VNP09GA": ("VIRSCGDRF_NRT", "VNP09GANRT061"),
    "VJ109GA": ("VIRSCGDRF_NRT", "VJ109GANRT061"),
}

# File patterns
# FIXME: Above, we distinguish between VJ1 and VNP.  Perhaps we should do the same here?
# This would be a generic pattern for viirs:
#   NOTE: Keep entire VIIRS identifier as one set (VNP|VJ1|<future>)
VIIRS_FILENAME_PATTERN = r"(VNP|VJ1)09GA.*\.A\d{7}\.h\d{2}v\d{2}\.\d{3}\.\d+\.h5"
# This would be a distinct pattern for the two currently-defined VIIRS files
#   NOTE: Also changing the varname pattern to "rhyme with" the ones above
#         ...because this could be made into a dictionary-lookup for even more VIIRS sats
#   NOTE: Changing name because "FILENAME" is ambigous: input or output or intermediate?
SRC_FILENAME_PATTERN_VJ1 = r"VJ1?09GA.*\.A\d{7}\.h\d{2}v\d{2}\.\d{3}\.\d+\.h5"
SRC_FILENAME_PATTERN_VNP = r"VNP?09GA.*\.A\d{7}\.h\d{2}v\d{2}\.\d{3}\.\d+\.h5"
SRC_FILENAME_PATTERN_MOD = r"MOD09GA.*\.A\d{7}\.h\d{2}v\d{2}\.\d{3}\.\d+\.hdf"

# Processing configuration
LOCK_TIMEOUT = int(os.getenv("DOWNLOAD_LOCK_TIMEOUT", "300"))
MAX_RETRIES = int(os.getenv("DOWNLOAD_MAX_RETRIES", "3"))

# Permissions (for PetaLibrary shared access)
TARGET_GROUP_ID = 2007559  # dscottgrp
FILE_PERMISSIONS = 0o775
DIR_PERMISSIONS = 0o775

# Maps product short name → its NRT input dir env var
PRODUCT_INPUT_DIR_ENVVAR = {
    "MOD09GA": "MOD09GA_NRT_DIR",
    "VNP09GA": "VNP09GA_NRT_DIR",
    "VJ109GA": "VJ109GA_NRT_DIR",
}

SUPPORTED_PRODUCTS = list(PRODUCT_INPUT_DIR_ENVVAR.keys())

PRODUCT_FILE_EXTENSION = {
    "MOD09GA": ".hdf",
    "VNP09GA": ".h5",
    "VJ109GA": ".h5",
}

PRODUCT_SOURCE_ID = {
    "MOD09GA": "MOD09GANRT061",
    "VNP09GA": "VNP09GANRT061",
    "VJ109GA": "VJ109GANRT061",
}

PRODUCT_OUTPUT_PREFIX = {
    "MOD09GA": "MODSCGDRF",
    "VNP09GA": "VNPSCGDRF",
    "VJ109GA": "VJ1SCGDRF",
}
