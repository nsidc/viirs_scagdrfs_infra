#!/bin/bash

# Get the scag repository
source ${PWD}/config/env.sh
cd ${TOPDIR}

if [ ! -d ${TOPDIR}/scag ]; then
    echo "Cloning scag repository."
    git clone git@github.com:nsidc/scag.git
fi

# Set environment variables and build executables
echo "Building executables in repositories..."

echo "Building scag"
cd ${TOPDIR}/scag
make build-alpine

cd $TOPDIR

echo "...done"
echo
