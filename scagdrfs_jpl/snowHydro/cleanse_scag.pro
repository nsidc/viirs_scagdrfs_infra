;+========================================================================
; :Author: Mary Jo Brodzik  <brodzik@>  
; :Copyright: (C) <2012> University of Colorado.
; :Version: $Id$
;
; Created 10/04/2012 
; National Snow & Ice Data Center, University of Colorado, Boulder
;-========================================================================*/

;+
;  reset_scag_data - sets NaNs to match .bip undefined locations
;                    and does thresholding and ROV checking on scag data

;
; :Params:
;    data : scag fraction data (e.g. snow_fraction, vegetation_fraction)
;    undef_idx : indices of locations for which the bip is undefined
;    undef_count : number of elements in undef_idx
;
; :Keywords:
;    rov=do_rov : do perform range-of-value checking
;    threshold=theshold : fraction threshold,
;      if /rov, input data values less than this will be set to zero
;    max_value: max data value
;      if /rov, input data values greater than this will be set to max_value
;   
; :Returns: modified data array, with:
;    undef_idx locations set to NaN
;    if ROV keyword set:
;      data values less than threshold set to 0.0
;      data values greater than max_value set to max_value
;
;-========================================================================
pro reset_scag_data, data, undef_idx, undef_count, $
                     rov=do_rov, $
                     threshold=threshold, $
                     max_value=max_value

  do_rov = keyword_set( do_rov ) ? 1 : 0
  threshold = 0 lt n_elements( threshold ) ? threshold : 0.0
  max_value = 0 lt n_elements( max_value ) ? max_value : 1.0

  if 0 lt undef_count then data[ undef_idx ] = !values.f_nan
  
  if do_rov then begin
      idx = where( threshold gt data, count )
      if 0 lt count then data[ idx ] = float(0.0D)
      
      idx = where( max_value lt data, count )
      if 0 lt count then data[ idx ] = max_value

   endif  
  return
end

;+========================================================================
;  reset_drfs_data - sets NaNs to match .bip undefined locations
;                    and does thresholding and ROV checking on drfs data
; :Params:
;    data : drfs forcing data (e.g. forcing.dat)
;    undef_idx : indices of locations for which the bip is undefined
;    undef_count : number of elements in undef_idx
;
; :Keywords:
;    rov=do_rov : do perform range-of-value checking
;    threshold=threshold : forcing threshold,
;      if /rov, input data values less than -32 will be set to NaN
;    max_value: max data value
;      if /rov, input data values greater max_value+32 will be set to NaN
;   
; :Returns: modified data array, with:
;    undef_idx locations set to NaN
;    if /ROV: 
;      data values -32.0 to 0.0 set to 0.0
;      data values 400.0 to 432.0 set to max_value
;      data greater than 432.0 = NaN
;      data less than -32.0 = NaN
;-========================================================================
pro reset_drfs_data, data, undef_idx, undef_count, $
                     rov=do_rov, $
                     threshold=threshold, $
                     max_value=max_value

  do_rov = keyword_set( do_rov ) ? 1 : 0
  threshold = 0 lt n_elements( threshold ) ? threshold : 0.0
  max_value = 0 lt n_elements( max_value ) ? max_value : 400.0
  error_value = 32.0 ;; W m^-2

  if 0 lt undef_count then data[ undef_idx ] = !values.f_nan

  if do_rov then begin
      
    ; Set values between -32.0 and 0 to 0.0D 
      idx = where( data lt threshold and data ge (threshold - error_value), count) 
      if 0 lt count then data[ idx ] = float(0.0D) 
    
    ; Set values less than -32.0 to nan        
      idx = where( data lt (threshold - error_value), count)
      if 0 lt count then data[ idx ] = !values.f_nan
    
    ; Set values between 400. and 432 to 400  
      idx = where( data gt max_value and data le (max_value + error_value), count)
      if 0 lt count then data[ idx ] = max_value
    
    ; Set values greater than 432. to nan  
      idx = where( data gt (max_value + error_value), count)
      if 0 lt count then data[ idx ] = !values.f_nan
            
  endif
 return
END 

;+========================================================================
;  reset_dvis_data - sets NaNs to match .bip undefined locations
;                    and does thresholding and ROV checking on drfs data
; :Params:
;    data : drfs deltavis data 
;    undef_idx : indices of locations for which the bip is undefined
;    undef_count : number of elements in undef_idx
;
; :Keywords:
;    rov=do_rov : do perform range-of-value checking
;    threshold: min data value
;      if /rov, input data values less than threshold will be set to NaN
;    max_value: max data value
;      if /rov, input data values greater max valuewill be set to NaN
;   
; :Returns: modified data array, with:
;    undef_idx locations set to NaN
;    if ROV keywords set:
;      data values less than 0.0 = NAN
;      data greater than 100 = NaN
;-========================================================================
pro reset_dvis_data, data, undef_idx, undef_count, rov=do_rov,$
                     threshold=threshold, max_value=max_value

  do_rov = keyword_set( do_rov ) ? 1 : 0
  threshold = 0 lt n_elements( threshold ) ? threshold : 0.0
  max_value = 0 lt n_elements( max_value ) ? max_value : 100.0

  if 0 lt undef_count then data[ undef_idx ] = !values.f_nan

  if do_rov then begin
      
      ;; Set values less than 0.0 to nan        
      idx = where( data lt threshold, count)
      if 0 lt count then data[ idx ] = !values.f_nan
    
      ;; Set values greater than 100. to nan  
      idx = where( data gt max_value, count)
      if 0 lt count then data[ idx ] = !values.f_nan
            
  endif 
 return
END  

;+========================================================================
;
;  cleanse_scag - cleans scag data for downstream processing,
;                 does bounds checking
;                 looks for NaNs in MOD09GA
;
; :Params:
;    mod09ga_file : MOD09GA file that corresponds to the scag data
;
; :Keywords:
;    THRESHOLD=threshold : in, optional, float, default 0.15
;      all "fraction" values below this threshold will be set to 0.0
;    SNOW_FRACTION=snow_fraction : in/out, optional,  fltarr
;      snow_fraction scag output data 
;    VEGETATION_FRACTION=vegetation_fraction : in/out, optional,  fltarr
;      vegetation_fraction scag output data 
;    ROCK_FRACTION=rock_fraction : in/out, optional,  fltarr
;      rock_fraction scag output data 
;    OTHER_FRACTION=other_fraction : in/out, optional,  fltarr
;      other_fraction scag output data 
;    SHADE_FRACTION=shade_fraction : in/out, optional,  fltarr
;      shade_fraction scag output data 
;    GRAIN_SIZE=grain_size : in/out, optional,  fltarr
;      grain_size scag output data
;    RMS=rms : in/out, optional,  fltarr
;      rms scag output data 
;    QUALITY=quality : in/out, optional,  fltarr
;      quality scag output data 
;    QUALITY_BITS=quality_bits : in/out, optional,  fltarr
;      quality_bits scag output data
;    TODO - Add in better docs to explain the DRFS inputs
;    FORCING=forcing : in/out, optional, fltarr
;      forcing data from DRFS
;    DELTAVIS=deltavis : in/out, optional, fltarr
;      deltavis
;
; :Returns: any input scag data arrays will be "cleansed" according to:
;    1) all layers:  except for band 5, which we know to be noisy
;       due to striping problem that we will fix with downstream
;       destriping algorithm, if any corresponding .bip pixel is undefined,
;       the scag pixel will be set to NaN
;    2) for some layers only:
;       any input scag values < threshold will be set to 0.0
;       any input scag values > max_value_for_this_data_type will be set to max_value
; 
; Return value will be 0 for success, or -1 for error
;
; Note that this routine will be most efficient if called with all
; scag layers to cleanse at the same time, because there is I/O overhead
; each time MOD09GA is opened to extract the .bip locations with undefined
; values
;
;-
function cleanse_scag, mod09ga_file, $
                       THRESHOLD=threshold, $
                       SNOW_FRACTION=snow_fraction, $
                       VEGETATION_FRACTION=vegetation_fraction, $
                       ROCK_FRACTION=rock_fraction, $
                       OTHER_FRACTION=other_fraction, $
                       SHADE_FRACTION=shade_fraction, $
                       GRAIN_SIZE=grain_size, $
                       RMS=rms, $
                       QUALITY=quality, $
                       QUALITY_BITS=quality_bits, $
                       FORCING=forcing, $
                       DELTAVIS=deltavis, $
                       VERBOSE=do_verbose

  threshold = 0 ne n_elements( threshold ) ? threshold : 0.15
  do_verbose = keyword_set( do_verbose ) ? 1 : 0
  
  max_fraction = float(1.0D)

  min_grain_size = float(0.0D)
  max_grain_size = float(1100.0D)
  
  min_forcing = float(0.0D)
  max_forcing = float(400.0D)

  max_deltavis = float(100.0D)
  min_deltavis = float(0.0D)
  
  ;; get bip from MOD09GA file
  if 0 ne extract_modis_reflectance(mod09ga_file, bip ) then begin
      message, "ERROR extracting data from mod09ga file: " $
               + mod09ga_file, $
               /info
      return, -1
  endif

  ;; ignore anything in band 5 of bip
  ;; band5_idx = 4
  ;; bip[ band5_idx,*,* ] = 0


  ;; mod09ga_undefined = -28672
  ;; bip-ify scales it by 0.1 and converts to integer
  ;; in extract_modis_reflectance, we do this by fix(x+0.5), which yields -2866
  ;; N.B. matlab-derived bips may be -2867, depending on rounding algorithm
  mod09ga_undefined = -28672
  bip_scale_factor = 0.1
  bip_undefined = fix( mod09ga_undefined * bip_scale_factor + 0.5 )

  ;; find the 2D locations where any input channel was undefined
  dims = size( bip, /dimensions )
  bip_mask = make_array( /byte, dimension=dims )
  idx = where( bip_undefined ge bip, count )
  if 0 lt count then bip_mask[ idx ] = 1
  mask = total( bip_mask, 1 )
  undef_idx = where( 0 lt mask, undef_count)
  message, string( undef_count ) + " pixels with the bip undefined.", /info

  if do_verbose then begin
      print, "> Identified " + string( undef_count ) $
             + " bip locations with at least one undefined reflectance in " $
             + mod09ga_file
  endif
  
  ;; for any layer that is input:
  ;;   set NaNs to match .bip undefined
  ;;   for fraction and grain_size layers, do range-of-values checks
  if 0 lt n_elements( snow_fraction ) then $
     reset_scag_data, snow_fraction, undef_idx, undef_count, $
                      /rov, threshold=threshold, max_value=max_fraction
  if 0 lt n_elements( vegetation_fraction ) then $
     reset_scag_data, vegetation_fraction, undef_idx, undef_count, $
                      /rov, threshold=threshold, max_value=max_fraction
  if 0 lt n_elements( rock_fraction ) then $
     reset_scag_data, rock_fraction, undef_idx, undef_count, $
                      /rov, threshold=threshold, max_value=max_fraction
  if 0 lt n_elements( other_fraction ) then $
     reset_scag_data, other_fraction, undef_idx, undef_count, $
                      /rov, threshold=threshold, max_value=max_fraction
  if 0 lt n_elements( shade_fraction ) then $
     reset_scag_data, shade_fraction, undef_idx, undef_count, $
                      /rov, threshold=threshold, max_value=max_fraction

  ;; grain_size ROVs are different from fraction ROVs
  if 0 lt n_elements( grain_size ) then $
     reset_scag_data, grain_size, undef_idx, undef_count, $
                      /rov, threshold=min_grain_size, max_value=max_grain_size

  ;; the rest of scag's output shouldn't have /rov done, just NaNs
  if 0 lt n_elements( rms ) then $
     reset_scag_data, rms, undef_idx, undef_count
  if 0 lt n_elements( quality ) then $
     reset_scag_data, quality, undef_idx, undef_count
  if 0 lt n_elements( quality_bits ) then $
     reset_scag_data, quality_bits, undef_idx, undef_count

  ;; forcing data SHOULD have /rov, /err, and NaNs
  if 0 lt n_elements( forcing ) then $
      reset_drfs_data, forcing, undef_idx, undef_count, /rov, $
                     threshold=min_forcing, max_value=max_forcing
                     
  ;; deltavis data SHOULD have /rov and NaNs
  if 0 lt n_elements( deltavis ) then $
      reset_dvis_data, deltavis, undef_idx, undef_count, /rov, $
                     threshold=min_deltavis, max_value=max_deltavis
                     
  return, 0

end
