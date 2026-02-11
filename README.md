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

{usage}


## Troubleshooting

{troubleshooting}


## Credit

This content was developed by the National Snow and Ice Data Center with funding from
multiple sources.
