;;
;; reads an SDS layer from a MODIS tile file
;;
;; 2008-03-26 M. J. Brodzik brodzik@nsidc.org 303-492-8263
;; National Snow & Ice Data Center
;; Copyright (C) 2008 University of Colorado
;;
;;
function read_modis_tile, filename, SD_NAME=sd_name, $
                          DATA=data, $
                          SCALE_FACTOR=scale_factor, $
                          VERBOSE=do_verbose

  status = -1

  if 1 gt n_params() then begin
      print, "usage: status = read_modis_tile ( filename ) "
      print, "       [, SD_NAME=sd_name ]"
      print, "       [, DATA=data ]"
      print, " ARGUMENTS:"
      print, "   filename : MOD09GA, MOD10A1 or MOD10A2 filename to read"
      print, " KEYWORDS:"
      print, "   SD_NAME=sd_name : name of SD to retrieve"
      print, "           default is 'Snow_Cover_Daily_Tile'"
      print, "           only works for v005 files"
      print, "   DATA=data : returned SDS layer data array"
      print, "   SCALE_FACTOR=scale_factor : returned data scale_factor"
      print, "   /VERBOSE : for verbose output"
      print, " Returns 0 for success, or in case of error,"
      print, " trys to clean up HDF mess and returns -1."
      return, status
  endif

  do_verbose = keyword_set( do_verbose ) ? 1 : 0
  
  if 0 eq n_elements( sd_name ) then begin
      sd_name = 'Snow_Cover_Daily_Tile'
  endif

  ;; open the hdf file
  sd_id = hdf_sd_start( filename )
  if do_verbose then message, "> Opened HDF file " + filename, /info

  ;; get the index number of the requested data layer
  ;; This is going to be different for v004 files (grrrhhhh)
  data_idx = hdf_sd_nametoindex( sd_id, sd_name )
  if -1 eq data_idx then begin
      message, "No layer in this file with sd_name=" + sd_name, /info
      hdf_sd_end, sd_id
      return, status
  endif

  ;; select the data layer, and extract its data
  sds_id = hdf_sd_select( sd_id, data_idx)
  hdf_sd_getdata, sds_id, data
  if do_verbose then message, "> Retrieved data layer " + sd_name, /info

  hdf_sd_getinfo, sds_id, HDF_TYPE=hdf_type
  if do_verbose then message, "> HDF type for this layer is " + hdf_type, /info

  attridx = hdf_sd_attrfind( sds_id, 'scale_factor' )
  if -1 eq attridx then begin

      message, "No scale_factor attribute for this layer.", /info
      scale_factor=!values.f_nan

  endif else begin

      hdf_sd_attrinfo, sds_id, attridx, data=scale_factor

  endelse

  ;; From what I can tell, the stored scale_factor attribute for
  ;; MOD09GA reflectances is the inverse of what it should be.  It's supposed to
  ;; be 0.0001, but is stored as 10000.  Apparently this problem
  ;; only affects reflectances, since the stored value for at least the
  ;; MOD09GA SolarZenith and SensorZenith is correct (0.01)
  ;; So I'm putting in this kluge, but only for reflectance data
  ;; JH 20211105 commenting out the folowing 4 linke  kludge to see if it corrects issues proocessing v061 instead of v006
  ;;if stregex( sd_name, 'sur_refl_b', /boolean ) then begin
  ;;    if do_verbose then message, "> Inverting stored reflectance scale_factor.", /info
  ;;    scale_factor = 1. / scale_factor
  ;;endif
  
  ;; close the eoshdf file
  hdf_sd_endaccess, sds_id
  hdf_sd_end, sd_id
  if do_verbose then message, "> Closed HDF file " + filename, /info
  status = 0

  return, status

end
