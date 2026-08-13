.ONESHELL:

SHELL = bash
.DEFAULT_GOAL := help
CONDA_ACTIVATE=source $$(conda info --base)/etc/profile.d/conda.sh ; conda activate
# CONDA_SCAG_ACTIVE := $(shell source $$(conda info --base)/etc/profile.d/conda.sh; conda info --envs | grep base | grep -c scag) # 0 or 1

.PHONY: help

SCAG_HOME:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

help: ## This help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build the C code locally with GCC
	export SCAG_COMPILER=gcc
	export SCAG_HOME=$(SCAG_HOME) # TODO: TOPDIR->HOME
	cd src
	make clean
	make all
	make install


## You must be on an alpine compile node to have access to the C compilers
## No versions specified here, but if we eventually need to build with
## netcdf modules, M.Hardman used these versions:
##      ml intel/2022.1.2
##      ml netcdf/4.8.1
##      ml udunits/2.2.25
## email from CURC (Trevor) Feb 2023 recommends always using intel
## compiler version
build-alpine: ## Build the C code on Alpine
	module purge all
	module load intel/2022.1.2
	export LOCALE=RCicc
	export SCAG_COMPILER=icc
	export SCAG_HOME=$(SCAG_HOME)

	cd src
	make clean
	make all
	make install


#####################################
###
### Store or build conda env.
###
env-create: ## Create the conda environment from suggested versions
	conda env create

env-create-from-lock: ## Create the conda environment from pinned versions
	conda env create -f environment-lock.yml

env-lock: ## Make environment-lock.yml
	conda env export | grep -v ^prefix > environment-lock.yml



#####################################
###
### Testing (Regression, Python, etc.)
###
test: test-setup test-scripts python-test regression

test-scripts:
	./scag.sh --test

test-setup: # download and unpack files needed for regression testing
	rm -fR tmp_test
	git clone --depth 1 https://github.com/nsidc/scag_test_data/
	cd scag_test_data/1_subset/
	mkdir -p LC08_L2SP_046027_20200316_20200822_02_T1
	tar xvf LC08_L2SP_046027_20200316_20200822_02_T1_subset_1500x10.tar -C LC08_L2SP_046027_20200316_20200822_02_T1

test-shellcheck:
	# Not run by default because it flags style issues that I currently do not have a workaround for.
	shellcheck -a -e 1090 -s bash -x $$(find . -name "*.sh")

regression: test-setup regression-bip regression-oli ## Run regression tests

regression-bip: # run BIPifier; make sure output unchanged from regression suite.
	if [[ ! $(CONDA_DEFAULT_ENV)x == "scagx" ]]; then $(CONDA_ACTIVATE) scag; fi
	# OLI
	./scripts/BIPifier.py \
		-o ./tmp_test/test.bip \
		-i ./scag_test_data/1_subset/LC08_L2SP_046027_20200316_20200822_02_T1
	diff --report-identical-files \
		./tmp_test/test.bip \
		./scag_test_data/2_scag_bip/LC08_L2SP_046027_20200316_20200822_02_T1.bip
	diff --report-identical-files \
		<(cat ./tmp_test/test.bip.meta | grep -v SOURCE_FILE)\
		<(cat ./scag_test_data/2_scag_bip/LC08_L2SP_046027_20200316_20200822_02_T1.bip.meta | grep -v SOURCE_FILE)
	# MODIS
	./scripts/BIPifier.py \
		-o ./tmp_test/test.bip \
		-i ./scag_test_data/1_subset/MOD09GA.A2022224.h09v04.061.2022226033159_subset.hdf
	diff --report-identical-files \
		./tmp_test/test.bip \
		./scag_test_data/2_scag_bip/MOD09GA.A2022224.h09v04.061.2022226033159.bip
	diff --report-identical-files \
		<(cat ./tmp_test/test.bip.meta | grep -v SOURCE_FILE) \
		<(cat ./scag_test_data/2_scag_bip/MOD09GA.A2022224.h09v04.061.2022226033159.bip.meta | grep -v SOURCE_FILE)


regression-oli: build
	rm -fR tmp_test
	./scag.sh -o ./tmp_test/OUT -w ./tmp_test/WORK -vv --debug \
		-i ./scag_test_data/2_scag_bip/LC08_L2SP_046027_20200316_20200822_02_T1.bip
	(cd tmp_test/WORK; (cd ../../scag_test_data/3_output/LC08/; md5sum *.bin) | md5sum --check)
	(cd tmp_test/OUT; (cd ../../scag_test_data/3_output/LC08/; md5sum *.tif) | md5sum --check)



#####################################
###
### Python BIPifier testing
###
# TODO: doctest
python-test: test-setup pre-commit pytest ## Run Python tests

pre-commit: # Git pre-commit tests
	if [[ ! $(CONDA_DEFAULT_ENV)x == "scagx" ]]; then $(CONDA_ACTIVATE) scag; fi
	black .
	flake8 .

pytest: # Run pytest
	if [[ ! $(CONDA_DEFAULT_ENV)x == "scagx" ]]; then $(CONDA_ACTIVATE) scag; fi
	python -m pytest;



FORCE: # dummy target

clean: ## Clean up
	rm -fR tmp tmp_test
	rm -fR scag_test_data
	rm -fR regression

clean-all: clean ## Really clean up
	(cd src; SCAG_HOME=$(SCAG_HOME) SCAG_COMPILER=gcc make clean)
	rm -fR bin
	rm -fR scag_test_data scag_test_data.zip
	rm -fR regression
	# conda env remove -n scag
