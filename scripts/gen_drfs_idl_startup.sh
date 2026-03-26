#!/bin/bash

# Creates a file with run commands that can be used
# to compile custom IDL routine

# Suggested output name to use for this routine:
#   drfs_idl_startup.bat
# So, the suggested usage is:
#   ./scripts/gen_drfs_idl_startup.sh ./scripts/drfs_idl_startup.bat
# which will:
#  create:  ./scripts/drfs_idl_startup.bat
#  output:  Successfully created: ./scripts/drfs_idl_startup.bat


# Use this output file with IDL by invoking with "-idl_startup <filename>", eg
#   idl  <IDL_SCRIPT_NAME>  -idl_startup <OUTPUT_OF_THIS_SCRIPT> [-args arg1 arg2 ...]

# This is needed because other forms of making IDL programs available
# are challenging because of IDL's case insensitivity which causes
# autoconversion of path-line strings to ALL UPPER CASE.

# Note: this script must be run at setup because it currently requires the
#       username to reference the correct file location, wihch

# Note: the following formulation of exiting this script
#       allows this script to be either "source"d or executed:
#    (return 0 2>/dev/null) && return || exit
# eg either of these will work:
#  ./<this_script.sh>  <-- with "execute" permission bit set
#  bash <this_script.sh>
#  source <this_script.sh>

# For user "scotts", this script should produce this output (uncommented):
#   .run /projects/scotts/scagdrfs_infra/scagdrfs_jpl/snowHydro/read_modis_tile.pro
#   .run /projects/scotts/scagdrfs_infra/scagdrfs_jpl/snowHydro/drfs_hdf_solar.pro
#   .run /projects/scotts/scagdrfs_infra/scagdrfs_jpl/snowHydro/extract_modis_reflectance.pro
#   .run /projects/scotts/scagdrfs_infra/scagdrfs_jpl/snowHydro/mod_drfs_v1_2.pro
#   .run /projects/scotts/scagdrfs_infra/scagdrfs_jpl/snowHydro/cleanse_scag.pro
#   .run /projects/scotts/scagdrfs_infra/scagdrfs_jpl/snowHydro/moddrfs_cleanse.pro


output_scriptname=$1
if [ -z $output_scriptname ]; then
  echo "No name provided for the file this script creates"
  (return 0 2>/dev/null) && return || exit
fi

if [ -z $DRFS_IDL_DIR ]; then
  echo "env variable DRFS_IDL_DIR is not set"
  echo "You might need to run ./config/env.sh"
  (return 0 2>/dev/null) && return || exit
fi

if [ -f ${output_scriptname} ]; then
  echo "Removing old: ${output_scriptname}"
  rm -v ${output_scriptname}
fi

declare -a idl_pro_file_names=(\
  'read_modis_tile.pro' \
  'drfs_hdf_solar.pro' \
  'extract_modis_reflectance.pro' \
  'mod_drfs_v1_2.pro' \
  'cleanse_scag.pro' \
  'moddrfs_cleanse.pro' \
 )

# Ensure that a new file is created in whatever directory is asked for
outdirname=$(dirname ${output_scriptname})
mkdir -p ${outdirname}
touch ${output_scriptname}

# Write the output batch file
echo "; ${output_scriptname}" >> ${output_scriptname}
echo "; IDL routines that can be compiled with -idl_startup cmdline option" >> ${output_scriptname}
echo "" >> ${output_scriptname}

for pro_file_name in ${idl_pro_file_names[@]}; do
  # Note the double >> to redirect into just-created (touch) file
  echo ".run ${DRFS_IDL_DIR}/${pro_file_name}" >> ${output_scriptname}
done

if [ -f ${output_scritpname}]; then
  echo "Successfully created: ${output_scriptname}"
else
  echo "ERROR:  FAILED TO CREATE  ${output_scriptname}"
fi
