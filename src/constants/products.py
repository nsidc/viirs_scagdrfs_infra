"""VIIRS product configuration."""

import os

# Concept IDs for different VIIRS products
LANCE_CONCEPT_ID_VJ1 = "C2781246545-LANCEMODIS"  # VJ109GA (NOAA-20) NRT
LANCE_CONCEPT_ID_VNP = "C2780105555-LANCEMODIS"  # VNP09GA (NPP) NRT

# Product short names
PRODUCT_SHORT_NAME_VJ1 = "VJ109GA_NRT"
PRODUCT_SHORT_NAME_VNP = "VNP09GA_NRT"

# File patterns
VIIRS_FILENAME_PATTERN = r"V[JN]P?09GA.*\.A\d{7}\.h\d{2}v\d{2}\.\d{3}\.\d+\.(hdf|h5)"

# Processing configuration
LOCK_TIMEOUT = int(os.getenv("DOWNLOAD_LOCK_TIMEOUT", "300"))
MAX_RETRIES = int(os.getenv("DOWNLOAD_MAX_RETRIES", "3"))

# Permissions (for PetaLibrary shared access)
TARGET_GROUP_ID = 2007559  # dscottgrp
FILE_PERMISSIONS = 0o775
DIR_PERMISSIONS = 0o775
