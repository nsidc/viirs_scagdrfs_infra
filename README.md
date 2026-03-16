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

### 3. Configure Earthdata credentials

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

  -p, --product [VJ1|VNP|both]
                          Which VIIRS product to download:
                          - VJ1: NOAA-20 (VJ109GA_NRT)
                          - VNP: NPP (VNP09GA_NRT)
                          - both: Download both products (default)

  -h, --help              Show help message and exit
```

## Download Specific Products
```bash
# Download only VJ109GA (NOAA-20)
./scripts/fetch-nrt.sh --product VJ1

# Download only VNP09GA (NPP)
./scripts/fetch-nrt.sh --product VNP

# Explicitly download both (same as default)
./scripts/fetch-nrt.sh --product both
```

Files are automatically organized by product and date in separate directories:

**VJ109GA (NOAA-20) files:**
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

## Troubleshooting

{troubleshooting}


## Credit

This content was developed by the National Snow and Ice Data Center with funding from
multiple sources.
