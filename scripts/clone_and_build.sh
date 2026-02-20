#!/bin/bash

# Get the scag and scagdrfs_jpl repositories
source ${PWD}/config/env.sh
cd ${TOPDIR}

if [ ! -d ${TOPDIR}/scag ]; then
    echo "Cloning scag repository."
    git clone git@github.com:nsidc/scag.git
fi
if [ ! -d ${TOPDIR}/scagdrfs_jpl ]; then
    echo "Cloning scagdrfs_jpl repository."
    git clone git@github.com:nsidc/scagdrfs_jpl.git
fi

# Set environment variables and build executables
echo "Building executables in repositories..."

echo "Building scag"
cd ${TOPDIR}/scag
make build-alpine

#echo "Building scagdrfs"
#cd ${TOPDIR}/scagdrfs_jpl
#ln -s pathdef_R2021b.m pathdef.m

cd $TOPDIR

echo "...done"
echo
