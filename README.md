<p align="center">
  <img alt="NSIDC logo" src="https://nsidc.org/themes/custom/nsidc/logo.svg" width="150" />
</p>


# VIIRS SCAGDRFS Infrastructure

{title} enables {audience} to {utility}.


## Level of Support

* This repository is fully supported by NSIDC. If you discover any problems or bugs,
  please submit an Issue. If you would like to contribute to this repository, you may fork
  the repository and submit a pull request.

See the [LICENSE](LICENSE) for details on permissions and warranties. Please contact
nsidc@nsidc.org for more information.


## Requirements

* Access to NSIDC Alpine compute environment
* NASA Earthdata Login credentials (https://urs.earthdata.nasa.gov/)
* Conda or Mamba package manager


## Installation

### 1. Clone the repository
```bash
cd /projects/$USER
git clone  viirs_scagdrfs_infra
cd viirs_scagdrfs_infra
```

### 2. Get an interactive node
```bash
 salloc --nodes=2 --ntasks=2 --qos=normal --partition=amilan --time=03:00:00 srun --pty $SHELL
```

### 3. Create conda environment
```bash
# Using mamba (faster)
mamba env create -f environment.yml

# or using build in script
./scripts/activate-viirs-conda.sh
```

### 4. Clone and buid scag C code

```bash
./scripts/clone_and_build.sh
```

### 5. Configure Earthdata credentials

Create a `.netrc` file in your home directory for authentication:
```bash
cat > ~/.netrc << EOF
machine urs.earthdata.nasa.gov
    login YOUR_USERNAME
    password YOUR_PASSWORD
EOF
chmod 600 ~/.netrc
```


## Usage

### Fetching NRT data

The primary script for downloading VIIRS NRT data is `fetch-nrt.sh`, which wraps the Python module for easier execution.

**Download both VJ109GA (NOAA-20) and VNP09GA (NPP) for the last 2 days:**
```bash
./scripts/fetch-nrt.sh
```

These are the options when running. NOTE: Most nrt data only exists for ~7 days.
```bash
./scripts/fetch-nrt.sh [OPTIONS]

Options:
  -s, --start-date TEXT    Start date for VIIRS NRT data download.
                          Format: YYYY-MM-DD or YYYYMMDD
                          Default: 2 days ago

  -e, --end-date TEXT     End date for VIIRS NRT data download (inclusive).
                          Format: YYYY-MM-DD or YYYYMMDD
                          Default: yesterday

  -P, --product TEXT      Product(s) to download. Can be specified multiple
                          times. Choices: MOD09GA, VNP09GA, VJ109GA
                          Default: VNP09GA, VJ109GA

  -h, --help              Show help message and exit
```

## Download Specific Products
```bash
# Download only VJ109GA (NOAA-20)
./scripts/fetch-nrt.sh --product VJ109GA

# Download only VNP09GA (NPP)
./scripts/fetch-nrt.sh --product VNP09GA

# Download multiple products
./scripts/fetch-nrt.sh --product VNP09GA --product VJ109GA
```

Files are automatically organized by product and date in separate directories:

**VJ109GA (NOAA-20) files:**
**NRT**
```
/pl/active/daac-production/VJ109GA/NRT/
├── 2026.02.01/
│   ├── VJ109GA_NRT.A2026032.h08v04.002.2026033012345.h5
│   ├── VJ109GA_NRT.A2026032.h09v04.002.2026033012346.h5
│   └── ...
├── 2026.02.02/
│   └── ...
└── 2026.02.03/
```
**FINAL**

```
/pl/active/daac-production/VJ109GA/FIN/
├── 2026.02.01/
│   ├── VJ109GA_NRT.A2026032.h08v04.002.2026033012345.h5
│   ├── VJ109GA_NRT.A2026032.h09v04.002.2026033012346.h5
│   └── ...
├── 2026.02.02/
```

**VNP09GA (NPP) files:**

```
/pl/active/daac-production/VNP09GA/NRT/
├── 2026.02.01/
│   ├── VNP09GA_NRT.A2026032.h08v04.002.2026033012345.h5
│   ├── VNP09GA_NRT.A2026032.h09v04.002.2026033012346.h5
│   └── ...
├── 2026.02.02/
│   └── ...
└── 2026.02.03/
```

### Running DRFS processing (TEMPORARY)

The files needed to run DRFS have been copied to this repository.  There are several requirements to be able to run DRFS in standalone mode:

- Be in the `scag` conda environment:
  - `conda activate scag`
- Run `. config/env.sh`
- Generate the `drfs_idl_startup.bat` file by running the generation script:
  - From "root" repo directory, run:
    - `./scripts/gen_drfs_idl_startup.sh ./scripts/drfs_idl_startup.bat`
  - NOTE: This only needs to be run the first time you set up the environment
- Run the `./scripts/run-drfs.sh` script
  - A script has been written with hardcoded values for that work for development
  - NOTE: this procedure requires that the MODIS .hdf file and the corresponding .bip and .bip_meta files already exist
  - From the "root" repo directory, run:
    - `./runonlydrfs.sh`
- This creates .dat, .bin, .mask, .tif output files.  The .tif files match exactly the .tif files created via `scagdrfs_infra`.  For the default values and operator_name `scotts`, the output files are:

```bash
ls -lrt /scratch/alpine/scotts/scagdrfs/working/2026.03.09/h09v05
total 373249
-rwxrwxr-x 1 scotts scottsgrp 80572911 Mar 10 02:03 MOD09GA.A2026068.h09v05.061.2026069014006.NRT.hdf
-rw-rw-r-- 1 scotts scottsgrp 80640000 Mar 10 09:41 MOD09GA.A2026068.h09v05.061.2026069014006.NRT.bip
-rw-rw-r-- 1 scotts scottsgrp      532 Mar 10 09:41 MOD09GA.A2026068.h09v05.061.2026069014006.NRT.bip.meta
-rw-rw-r-- 1 scotts scottsgrp 11520000 Mar 26 11:29 MOD09GA.A2026068.h09v05.061.2026069014006.NRT.SolarZenith_1.dat
-rw-rw-r-- 1 scotts scottsgrp 11520000 Mar 26 11:29 MOD09GA.A2026068.h09v05.061.2026069014006.NRT.SolarAzimuth_1.dat
-rw-rw-r-- 1 scotts scottsgrp 23040000 Mar 26 11:30 MOD09GA.A2026068.h09v05.061.2026069014006.NRT.deltavis.dat
-rw-rw-r-- 1 scotts scottsgrp 23040000 Mar 26 11:30 MOD09GA.A2026068.h09v05.061.2026069014006.NRT.forcing.dat
-rw-rw-r-- 1 scotts scottsgrp 23040000 Mar 26 11:30 MOD09GA.A2026068.h09v05.061.2026069014006.NRT.drfs.grnsz.dat
-rw-rw-r-- 1 scotts scottsgrp 23040000 Mar 26 11:30 MOD09GA.A2026068.h09v05.061.2026069014006.NRT.forcing.cleanse.dat
-rw-rw-r-- 1 scotts scottsgrp 23040000 Mar 26 11:30 MOD09GA.A2026068.h09v05.061.2026069014006.NRT.deltavis.cleanse.dat
-rw-rw-r-- 1 scotts scottsgrp 23040000 Mar 26 11:30 MOD09GA.A2026068.h09v05.061.2026069014006.NRT.drfs.grnsz.cleanse.dat
-rw-rw-r-- 1 scotts scottsgrp  5760000 Mar 26 11:30 MODSCGDRF_NRT_DELTAVIS_h09v05_MOD09GANRT061_20260309_V01.1.bin.Unmask
-rw-rw-r-- 1 scotts scottsgrp 11520000 Mar 26 11:30 MODSCGDRF_NRT_drfsGS_h09v05_MOD09GANRT061_20260309_V01.1.bin.Unmask
-rw-rw-r-- 1 scotts scottsgrp 11520000 Mar 26 11:30 MODSCGDRF_NRT_RF_h09v05_MOD09GANRT061_20260309_V01.1.bin.Unmask
-rw-rw-r-- 1 scotts scottsgrp  5760000 Mar 26 11:30 MODSCGDRF_NRT_DELTAVIS_h09v05_MOD09GANRT061_20260309_V01.1.bin.mask
-rw-rw-r-- 1 scotts scottsgrp 11520000 Mar 26 11:30 MODSCGDRF_NRT_drfsGS_h09v05_MOD09GANRT061_20260309_V01.1.bin.mask
-rw-rw-r-- 1 scotts scottsgrp 11520000 Mar 26 11:30 MODSCGDRF_NRT_RF_h09v05_MOD09GANRT061_20260309_V01.1.bin.mask
-rw-rw-r-- 1 scotts scottsgrp   208559 Mar 26 11:31 MODSCGDRF_NRT_RF_h09v05_MOD09GANRT061_20260309_V01.1.Unmask.tif
-rw-rw-r-- 1 scotts scottsgrp   221398 Mar 26 11:31 MODSCGDRF_NRT_drfsGS_h09v05_MOD09GANRT061_20260309_V01.1.Unmask.tif
-rw-rw-r-- 1 scotts scottsgrp   106395 Mar 26 11:31 MODSCGDRF_NRT_DELTAVIS_h09v05_MOD09GANRT061_20260309_V01.1.Unmask.tif
-rw-rw-r-- 1 scotts scottsgrp   269919 Mar 26 11:31 MODSCGDRF_NRT_RF_h09v05_MOD09GANRT061_20260309_V01.1.tif
-rw-rw-r-- 1 scotts scottsgrp   160929 Mar 26 11:31 MODSCGDRF_NRT_DELTAVIS_h09v05_MOD09GANRT061_20260309_V01.1.tif
-rw-rw-r-- 1 scotts scottsgrp   273074 Mar 26 11:31 MODSCGDRF_NRT_drfsGS_h09v05_MOD09GANRT061_20260309_V01.1.tif
```

### Running SCAGDRFS processing

```bash
./scripts/run-scagdrfs.sh --product VNP09GA --start-date 2026-03-11

# Run for MODIS
./scripts/run-scagdrfs.sh --product MOD09GA --start-date 2026-03-11
```

Currently supported products (work in progress): `MOD09GA`, `VNP09GA`, `VJ109GA`.

Working directories are organized by product under `$WORK_DIR`:
```
/scratch/alpine/$USER/scagdrfs/working/
├── MOD09GA/
│   └── 2026.03.11/h08v04/
├── VNP09GA/
│   └── 2026.03.11/h08v04/
└── VJ109GA/
    └── 2026.03.11/h08v04/
```


## Testing

The test suite lives in `tests/` and is split into three categories. `pytest.ini` at the repo root sets `pythonpath = .` so imports resolve correctly from any directory.

### Unit tests

Tests for path derivation, product registry, and utility helpers. No flags required and no filesystem access needed — safe to run anywhere.

```bash
pytest tests/test_constants_and_util.py
```

### DRFS regression tests

Compares DRFS binary outputs (`.bin.mask`, `.bin.Unmask`) against golden reference files stored in PetaLibrary. Tests shape, dtype, pixel-level closeness, value statistics, and masked pixel counts. Tolerances are set for IDL-to-Python comparison (`rtol=1e-3`, `atol=1.0`).

Golden files live at:
```
/pl/active/daac-production/drfs_regression/golden/<tile>/
```

```bash
pytest tests/test_drfs_regression.py \
  --date 20260309 \
  --region onetile \
  --product MOD09GA
```

To test exact byte reproducibility between two IDL runs, add `-m idl_only`:
```bash
pytest tests/test_drfs_regression.py \
  --date 20260309 \
  --region onetile \
  --product MOD09GA \
  -m idl_only
```

### SCAG regression tests

Compares SCAG binary outputs against golden reference files. Tests two stages:

- **Stage 1 — Raw SCAG bins** (output of `scag_sort`, before masking): `grnsz`, `other`, `rms`, `rock`, `shade`, `snow`, `veg`
- **Stage 2 — Masked/unmasked outputs** (output of `mask_scag`): `GS`, `ICE`, `ROCK`, `SHADE`, `SNOW`, `VEG`, each with `.bin.mask` and `.bin.Unmask` variants

Since SCAG is deterministic Python + binary (no IDL), all tests use exact comparison — byte-for-byte hash is a first-class test, not optional.

Golden files live at:
```
/pl/active/daac-production/scag_regression/golden/<tile>/
```

```bash
pytest tests/test_scag_regression.py \
  --date 20260518 \
  --region onenztile \
  --product VJ109GA
```

### Running all tests

```bash
# Unit tests only (no flags, runs anywhere)
pytest tests/test_constants_and_util.py

# All regression tests
pytest tests/test_drfs_regression.py --date 20260309 --region onetile --product MOD09GA
pytest tests/test_scag_regression.py --date 20260518 --region onenztile --product VJ109GA
```

Available `--region` values are defined in `src/constants/tiles.ini`:
```
WESTERN_US, US_ALASKA, NZ_ALPS, AM_ANDES, US, EUR_ALPS,
CANADA, AS_HIMILAYA, ARCTIC, AM_SOUTH_CENTRAL, US_HAWAII,
ATLANTIC_ISLES, ONETILE, ONENZTILE
```


## Troubleshooting

{troubleshooting}


## Credit

This content was developed by the National Snow and Ice Data Center with funding from
multiple sources.
