"""VIIRS product configuration."""

import os

# Concept IDs for different VIIRS products
# TODO: Is there also a non-NRT concept-id for each of these?
# RM NOTE: The concept-id is definitely different for not NRT. 
LANCE_CONCEPT_ID_VNP = "C2780105555-LANCEMODIS"  # VNP09GA (NPP) NRT
LANCE_CONCEPT_ID_VJ1 = "C2781246545-LANCEMODIS"  # VJ109GA (NOAA-20) NRT

# Product short names
PRODUCT_SHORT_NAME_VNP = "VNP09GA_NRT"
PRODUCT_SHORT_NAME_VJ1 = "VJ109GA_NRT"

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

# Processing configuration
LOCK_TIMEOUT = int(os.getenv("DOWNLOAD_LOCK_TIMEOUT", "300"))
MAX_RETRIES = int(os.getenv("DOWNLOAD_MAX_RETRIES", "3"))

# Permissions (for PetaLibrary shared access)
TARGET_GROUP_ID = 2007559  # dscottgrp
FILE_PERMISSIONS = 0o775
DIR_PERMISSIONS = 0o775
