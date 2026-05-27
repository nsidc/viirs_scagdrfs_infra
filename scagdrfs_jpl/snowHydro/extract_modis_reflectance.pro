;;
;; extract_modis_reflectance -
;; reads the reflectance data from a MOD09GA file, and creates a bip array.
;;
;; A bip array is:
;;   dimensions ( nchannels, ncols, nrows )
;;   channels ordered 3,4,1,2,5,6,7
;;   Stored reflectance data in hdf files are scaled by 10000.
;;   bip expects values to be scaled by 1000.
;;
;; If the bip array needs to be written to an external file, for
;; exchange with Painter, Just use writeu, lun, bip
;;
;; COLSTART/END and ROWSTART/END may be used to designate a subset
;; of the original data to save.  The default is the entire MODIS tile 
;; (2400x2400)
;;
;; 2008-05-23 M. J. Brodzik brodzik@nsidc.org 303-492-8263
;; National Snow & Ice Data Center
;; Copyright (C) 2008 University of Colorado
;;
;;
function extract_modis_reflectance, filename, bip, $
                                    VERBOSE=do_verbose, $
                                    BIP_FILENAME=bip_filename, $
                                    NCOLS=ncols, NROWS=nrows, $
                                    COLSTART=colstart, COLEND=colend, $
                                    ROWSTART=rowstart, ROWEND=rowend

  status = -1

  if 2 gt n_params() then begin
      print, "usage: status = extract_modis_reflectance ( filename, bip ) "
      print, " ARGUMENTS:"
      print, "   filename : MOD09GA filename to read"
      print, "   bip : extracted bip array"
      print, " KEYWORDS: "
      print, "   BIP_FILENAME=bip_filename : bip filename to write"
      print, "     output data will be bands 3,4,1,2,5,6,7, with"
      print, "     2-byte reflectances scaled by 1000"
      print, "   NCOLS=ncols : number of cols in each layer (default is 2400)"
      print, "   NROWS=nrows : number of rows in each layer (default is 2400)"
      print, "   COLSTART=colstart : subset column start (default is 0)"
      print, "   COLEND=colend : subset column end (default is ncols - 1)"
      print, "   ROWSTART=rowstart : subset row start (default is 0)"
      print, "   ROWEND=rowend : subset row end (default is nrows - 1)"
      print, "   VERBOSE : for verbose output"
      print, " Returns 0 for success, or in case of error,"
      print, " trys to clean up HDF mess and returns -1."
      return, status
  endif

  do_verbose = keyword_set( do_verbose ) ? 1 : 0
  do_write_bip = 0 ne n_elements( bip_filename ) ? 1 : 0
  if 0 eq n_elements( ncols ) then ncols = 2400
  if 0 eq n_elements( nrows ) then nrows = 2400
  if 0 eq n_elements( colstart ) then colstart = 0
  if 0 eq n_elements( colend ) then colend = ncols - 1
  if 0 eq n_elements( rowstart ) then rowstart = 0
  if 0 eq n_elements( rowend ) then rowend = nrows - 1
  
  sd_names = 'sur_refl_b' $
             + string( [ 3, 4, 1, 2, 5, 6, 7 ], format='(I2.2)' ) $
             + '_1'
  scale = 0.1
  nchannels = n_elements( sd_names )
  bip = intarr( nchannels, ncols, nrows )

  ;; Read the reflectance data, scale it, convert to short int, and
  ;; save it in the output array
  for i=0, nchannels - 1 do begin
      
      status = read_modis_tile( filename, sd_name=sd_names[ i ], data=refl )
      if 0 ne status then begin
          message, "Error reading " + sd_names[ i ] + " layer from " $
                   + filename, /info
          return, status
      endif
      if do_verbose then print, "> Next band orig   ROV=", min( refl ), max( refl )
      refl = fix( refl * scale + 0.5 )
      if do_verbose then print, "> Next band scaled ROV=", min( refl ), max( refl )
      bip[ i, *, * ] = refl

  endfor

  ;; Subset the data arrays
  bip = bip[ *, colstart:colend, rowstart:rowend ]

  openw, 19, 'ohmygod.dat'
  writeu, 19, bip
  close, 19
  print,'Wrote bip to: ohmygod.dat'

  if do_write_bip then begin
      openw, lun, bip_filename, /get_lun
      writeu, lun, bip
      free_lun, lun
      message, "Wrote scaled reflectance data to bip file="+bip_filename, /info
  endif

  if do_verbose then begin
      print, "> Dimensions of bip array are "
      help, bip
  endif
  
  return, 0

end
