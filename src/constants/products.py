"""VIIRS product configuration."""

import os

# VIIRS product information
PRODUCT_SHORT_NAME = "VJ109GA_NRT"
PRODUCT_CONCEPT_ID = os.getenv("VJ109GA_CONCEPT_ID", "C2565894243-LAADS")

# File patterns
VIIRS_FILENAME_PATTERN = r"VJ109GA\.A\d{7}\.h\d{2}v\d{2}\.\d{3}\.\d+\.hdf"

# Processing configuration
LOCK_TIMEOUT = int(os.getenv("DOWNLOAD_LOCK_TIMEOUT", "300"))
MAX_RETRIES = int(os.getenv("DOWNLOAD_MAX_RETRIES", "3"))

# Permissions (for PetaLibrary shared access)
TARGET_GROUP_ID = 2007559  # dscottgrp
FILE_PERMISSIONS = 0o775
DIR_PERMISSIONS = 0o775
