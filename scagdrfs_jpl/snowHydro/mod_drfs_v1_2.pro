FUNCTION RETURN_BUNDLE, ndgsi=ndgsi, ndsi=ndsi, snow=snow, grsz=grsz, cumwts=cumwts, deltarad=deltarad, radforc=radforc

; This function returns a snowbundle filled with FLAG values if there was NO snow found
; We added this so there is always an output for DRFS. AB: 2/5/13

    print, ' NO SNOW FOUND, RETURNING SNOWBUNDLE '

  ; THIS WILL ALWAYS BE 2400 x 2400 x 7
    snowbundle = fltarr(2400,2400,7)
    snowbundle(*,*,0) = ndgsi
    snowbundle(*,*,1) = ndsi
    snowbundle(*,*,2) = snow
    snowbundle(*,*,3) = grsz
    snowbundle(*,*,4) = cumwts
    snowbundle(*,*,5) = deltarad
    snowbundle(*,*,6) = radforc

    RETURN, SNOWBUNDLE

END

; ####################################################################################################
; ####################################################################################################
; ####################################################################################################

FUNCTION find_irspec_v1_2, sza=sza, elev=elev, dir_arr=dir_arr, dif_arr=dif_arr, ii=ii, jj=jj

  ; This function returns a weighted average spectrum based on SBDART spectra for discrete solar zenith angles
  ; and elevation bands, based on spectra created from the SBDART.z5to70.cmd file.
  ; AB: 1/10/2012
  ;******************************************

  ; Create Zenith and Elevation Arrays based on those used in SBDART
  zenith_array = [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0, 55.0, 60.0, 65.0, 70.0]
  elevation_array =  [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0]

  ; ------   Determine the nearest irradiance spectrum for a given solar zenith angle and elevation   --------

  ; Finds the location of the lower bounding spectrum in the array
  zenith_loc = min(zenith_array - sza, min_subscript, /absolute)
  z_sub = min_subscript

  ; mini is the lower bounding sza and maxi is the upper bound sza
  mini = zenith_array[z_sub]

  ; When z_sub is greater than the mean it defaults to the higher subscript, thus it has to be corrected here.
  if sza lt mini then begin
    z_sub = z_sub-1
    if z_sub eq -1 then z_sub=0
    mini = zenith_array[z_sub]
    maxi = zenith_array[z_sub+1]
  endif

  ; When z_sub is less than the mean, between the upper and lower bound sza it chooses the correct subscript.
  if z_sub ge 13 then z_sub=0
  maxi = zenith_array[z_sub+1]

  ; Determine percent distance of the input solar zenith angle from the lower-bound spectrum.
  ; 5 is a constant, as each SBDART spectrum 5 degrees apart.
  weight = 1 - ((maxi-sza)/ 5)

  ; ------ Elevation Calculations ---------

  elev_loc = min(elevation_array - elev, min_subscript, /absolute)
  e_sub = min_subscript

  ; Lower and Upper bound elevation
  e_mini = elevation_array[e_sub]

  ; When z_sub is greater than the mean it defaults to the higher subscript, thus it has to be corrected here.
  if elev lt e_mini then begin
    e_sub = e_sub-1
    if e_sub eq -1 then e_sub=0
    e_mini = elevation_array[e_sub]
    e_maxi = elevation_array[e_sub+1]
  endif

  ; When e_sub is less than the mean, between the upper and lower bound elevations it chooses the correct subscript.
  e_maxi = elevation_array[e_sub+1]

  ; ----- Created direct and diffuse irradiance spectra --------------

  ; Create bounding sza direct irradiance arrays
  dir_min_array = dir_arr[*,z_sub,e_sub]
  dir_max_array = dir_arr[*,z_sub+1,e_sub+1]

  ; Create bounding sza diffuse irradiance arrays
  dif_min_array = dif_arr[*,z_sub,e_sub]
  dif_max_array = dif_arr[*,z_sub+1 ,e_sub+1]

; Created direct irradiance spectrum weighted mean
  direct_input = weight * (dir_max_array - dir_min_array) + dir_min_array

; Created diffuse irradiance spectrum weighted mean
  diffuse_input = weight * (dif_max_array - dif_min_array) + dif_min_array

; Create output array
  outfile = fltarr(2,216)
  outfile[0,*] = direct_input
  outfile[1,*] = diffuse_input

;  plot, dir_min_array
;  oplot, dir_max_array
;  oplot, direct_input, line = 2

return, outfile

end

; ####################################################################################################
; ####################################################################################################
; ####################################################################################################

FUNCTION drfs_irradiance_v1_2, solar_zenith_angle=solar_zenith_angle, elev=elev,cosine_illumination_angle=cosine_illumination_angle,$
                                dir_arr=dir_arr, dif_arr=dif_arr, ii=ii, jj=jj


; ex: drfs_irradiance, sbdart_in='SBDART.z5to70.out', nb=216, ns=14, nl=19, slop_ang=45, solar_zen=45, elev=3 , asp_ang=45, solar_az=160

; SBDART.z5to70.out created using SBDART on snow.jpl.nasa.gov server, with paramaters:
;   idatm=  3
;   isat=   -3
;   isalb=  1
;   iout=   10
;   sza=    5.0 10.0 15.0 20.0 25.0 30.0 35.0 40.0 45.0 50.0 55.0 60.0 65.0 70.0
;   zpres=  0.0 0.5 1.0 1.5 2.0 2.5 3.0 3.5 4.0 4.5 5.0 5.5 6.0 6.5 7.0 7.5 8.0 8.5 9.0
;
; nb = 224 spectral bands
; ns = 14 solar zenith angles (i.e, sza; 1 = 5.0 , 2 = 10.0, 3 = 15.0, etc... 13 = 70.0)
; nl = 19 elevation bands (i.e., zpres: 1 = 0.0, 2 = 0.5, 3 = 1.0, etc... 18 = 9.0)
; cosine_illumination_angle = cosine_illumination_angle (calculated in mod_drfs_v1.)
; solar_zenith_angle = solar zenith angle in degrees  (0 - 70)
; elev = elevation km   (0. - 9.)


; AB 01.10.12

;*****************************************************************************************

; ------------- CREATE TOTAL and DIRECT IRRADIANCE ARRAYS -----------------------------------------------------
; This step needs to be done if a new SBDART file is created, other than SBDART.z5to60.txt (ab:2/4/12)
;
;   ;Create template for ascii for SBDART input
;    result = ascii_template(sbdart_in, browse_lines=60000)
;
;   ;Read SBDART file
;    array = read_ascii(sbdart_in, template=result)
;
;   ;Pull total irradiance from structure
;    total = array.field7
;
;   ;Pull direct irradiance from structure
;    direct = array.field9

 ;save, total,  filename = '/Users/annbryant/Documents/variables/total'
 ;save, direct, filename = '/Users/annbryant/Documents/variables/direct'


; ------------ CORRECT SPECTRAL IRRADIANCE FOR SLOPE, ASPECT, SOLAR ZENITH, AND SOLAR AZIMUTH ---------------------

; Pull appropriate array from SBDART for elevation and sza

    result = find_irspec_v1_2(sza=solar_zenith_angle, elev=elev, dir_arr=dir_arr, dif_arr=dif_arr, ii=ii, jj=jj)

    direct_input = result[0,*]
    diffuse_input = result[1,*]

    ; Correct the spectra

    corr_irrad = (cosine_illumination_angle * direct_input) + diffuse_input

; Check Spectra

;  window,2
;  wshow,2
;  plot,  (direct_input+diffuse_input),  thick = .5, background = 255, color = 0
;    oplot, direct_input,                thick = 1 , color = 50
;    oplot, diffuse_input,               thick = 2 , color = 100
;    oplot, corr_irrad,                  thick = 1 , color = 100

return, corr_irrad

end

; ####################################################################################################
; ####################################################################################################
; ####################################################################################################

FUNCTION MOD09GA_FORCE_WEIGHT_v1_2,comps_dir=comps_dir, rfl=rfl, ns=ns, nl=nl, nb=nb,locale=locale,$ ;, success=success, $
                                   solarzenith=solarzenith, elev=elev, cosine_illumination_angle=cosine_illumination_angle,$
                                   dir_arr=dir_arr, dif_arr=dif_arr,thresh=thresh, year=year, doy=doy, h=h, v=v
;
; MOD09GA_FORCE_WEIGHT_GENERAL
;
;   calculate dust radiative forcing from MODIS MOD09GA surface reflectance data
;
; Author: T.H.Painter
;   thomas.painter@jpl.nasa.gov
;
; Revisions:
;   May.2011
;   revised hard coding
;   C. Goodale, cameron.e.goodale@jpl.nasa.gov
;
;   July.11.2011
;   removed all cloud masking from code
;   T. H. Painter, thomas.painter@jpl.nasa.gov
;
;   Feb.3.2012
;   Inserted drf_irradiace function to return irradiance spectrum based on solar and terrain geometry.
;   AB, anniebryant@gmail.com
;
;**************************************************************************************************
;
  FLAG = -9999.99

;  ; This is a list of the wavelengths of MODIS bands
  openr,1,comps_dir + 'MODIS.wvl' ; ***** TO DO: PATH *****
  MODISwvl = fltarr(7)
  readf,1,MODISwvl
  close,1

  ; This is a list of the wavelengths of AVIRIS bands
  openr,1,comps_dir + 'irrad10nm.wvl' ; ***** TO DO: PATH *****
  AVIRIS_wvl = fltarr(2,216)
  readf,1,AVIRIS_wvl
  close,1

; Convert AVIRIS wavelenths from um to nm
  AVIwvl = ((AVIRIS_wvl[0,*]) * 1000)

; Reform bip surface reflectances to 2 dimensions
  b1 = reform(rfl(0,*,*))*1.0
  b2 = reform(rfl(1,*,*))*1.0
  b3 = reform(rfl(2,*,*))*1.0
  b4 = reform(rfl(3,*,*))*1.0
  b5 = reform(rfl(4,*,*))*1.0
  b6 = reform(rfl(5,*,*))*1.0

; Determine the location of maximum surface reflectance in band 1
  maxb1 = max(b1)
  pos = where(b1 eq maxb1)

; Establish output arrays
  ndsi  = fltarr(ns,nl)
  ndgsi = fltarr(ns,nl)
  snow  = fltarr(ns,nl)
  grsz  = fltarr(ns,nl)
  cumwts = fltarr(ns,nl)
  deltarad = fltarr(ns,nl)
  radforc = fltarr(ns,nl)

  ndsi(*,*)  = FLAG
  ndgsi(*,*) = FLAG
  snow(*,*)  = FLAG
  grsz(*,*)  = FLAG
  cumwts(*,*) = FLAG
  deltarad(*,*) = FLAG
  radforc(*,*) = FLAG

;  --------------------------- Vegetation mask added by AB and THP 3/8/12 -----------------------------------

; Validation Sites only for H09V05
  SASP = [1203,502]
  SBSP = [1200,502]
  GMSP = [1459,227]

if thresh eq 1 and h ne '9' or v ne '5' then begin ; We want to use the thresh if we are not comparing DRFS to Tower data.

; Establish what the value of band 3 would be if along the slope line between band 2 and band 4
  b3_thresh = (((b4 - b2 )/2) + b2)

; Determine if the value of band three is less than the threshold, i.e. there is a concavity in the spectrum
  pos_veg = where(b3 lt b3_thresh)

  b1(pos_veg) = FLAG
  b2(pos_veg) = FLAG
  b3(pos_veg) = FLAG
  b4(pos_veg) = FLAG
  b5(pos_veg) = FLAG
  b6(pos_veg) = FLAG

endif

;  ****  If we are looking at tower data, we don't want those pixels masked ****

if thresh eq 1 and h eq '9' and v eq '5' then begin

; Mask each band for vegetation but not the TOWER locations
  mask = fltarr(2400,2400)
  mask(SASP[0],SASP[1]) = 1.
  mask(SBSP[0],SBSP[1]) = 1.
  mask(GMSP[0],GMSP[1]) = 1.

; Establish what the value of band 3 would be if along the slope line between band 2 and band 4
  b3_thresh = (((b4 - b2 )/2) + b2)

; Determine if the value of band three is less than the threshold, i.e. there is a concavity in the spectrum
  pos_veg = where((b3 lt b3_thresh and mask lt 1))

  b1(pos_veg) = FLAG
  b2(pos_veg) = FLAG
  b3(pos_veg) = FLAG
  b4(pos_veg) = FLAG
  b5(pos_veg) = FLAG
  b6(pos_veg) = FLAG

endif

; Write b1 for comparison to: idl_b1_veg.dat
; Done.  b1 is the same as python version

; ------------------------------ Determine snow location and snow grainsize -----------------------

; Establish region for calculations based on snow reflectance in bands 4 and 5
; Note: confirmed pos is same as computed in python
  pos = where((b4 gt 0) and (b5 gt 0),cnt)

  ; Return FLAGGED bundle if no POS values are found
  IF cnt EQ 0 THEN BEGIN
      no_snow_bundle = RETURN_BUNDLE(ndgsi=ndgsi, ndsi=ndsi, snow=snow, grsz=grsz, cumwts=cumwts, deltarad=deltarad, radforc=radforc)
      return, no_snow_bundle
  ENDIF

  ; Compute NDSI using a band ratio and place value in array
  IF cnt NE 0 THEN BEGIN

    ndsi(pos) = (b2(pos)-b6(pos))/(b2(pos)+b6(pos))

    ; Determine snow covered pixels, where NDSI is greater than 1 and band 2 reflectance is gt than .5
    a=where((ndsi gt 0.1),cnt1)

    ; If NO snow is found, snowbundle is returned without any values (AB:  2/4/13)
    IF cnt1 EQ 0 THEN BEGIN
      no_snow_bundle = RETURN_BUNDLE(ndgsi=ndgsi, ndsi=ndsi, snow=snow, grsz=grsz, cumwts=cumwts, deltarad=deltarad, radforc=radforc)
      return, no_snow_bundle
    ENDIF

    ; If snow IS found begin
    IF cnt1 GT 0 THEN BEGIN
      snow(pos) = 0.0
      snow(where((ndsi gt 0.1) and (b2 gt 0.5))) = 1.0 ; Thresholds determined by T. Painter

      ; Compute NDGSI (Normalized Difference Grainsize Index) and place value in array
      ndgsi(pos) = (b4(pos) - b5(pos)) / (b4(pos) + b5(pos))

      ; If there are any non-snow pixels, insert FLAG values
      b=where((snow eq 0),cnt2)

      IF cnt2 GT 0 THEN ndgsi(where(snow eq 0.0))=FLAG
      IF cnt2 GT 0 THEN cumwts(where(snow eq 0.0))=FLAG

      ; --------------------------- Computing Radiative Forcing -----------------------------------------
      ;   These calculations determining radiative forcing by taking the difference between a modeled
      ;   clean-snow spectrum (based on a measured grainsize) and a measured snow-spectrum, then multiplying
      ;   the difference between incoming solar irradiance in the visible wavelenghts.

      print,' Starting to compute radiative forcing at:      ' , SYSTIME(0)
      print,'       '

      ;print to log (CGOODALE addition) ; Cam, you'll have to set this up how you like it.
      ;openw,100,'DustForc.log'
      ;close,100

      ; Pre-load all of the ndgsi and sli files
      ndgsiluts = fltarr(13,2,110)
      slis = fltarr(13,7,110)
      zenith_values = [15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75]
      ndgsilut = fltarr(2,110)
      sli = fltarr(7,110)
      for i_zv=0,12 do begin
        sza=zenith_values[i_zv]

        file_ndgsi      = strcompress(string(comps_dir + 'MODIS.z',sza,'.ndgsi'),/remove_all) ; ***** TO DO: PATH *****
        openr,1,file_ndgsi
        readf,1,ndgsilut
        ndgsiluts[i_zv, *, *] = ndgsilut(*, *)
        close,1

        ; These are the clean-spectra for MODIS per solar zenith angle.
        file_sli        = strcompress(string(comps_dir + 'MODIS.z',sza,'.sli'),/remove_all) ; ***** TO DO: PATH *****
        openr,1,file_sli
        readu,1,sli
        slis(i_zv, *, *) = sli
        close,1

      endfor


      ; Create outfile for irradiance measurements

      ; Note: changed the order of i,j so that it matches the python np.where() ordering...
      ;for i=0,ns-1 do begin
      for j=0, nl-1 do begin
        for i=0,ns-1 do begin
          ii = i
          jj = j
          ; FLAGGED PIXELS remain FLAGGED
          if (ndgsi(i,j) eq FLAG) then begin
            grsz(i,j) = FLAG
          endif else begin
            ;-------------------- OPEN APPROPRIATE NDGSI LUT FILES AND SLI FILES BASED ON SZA ------------
            ; NOTE: This peice of code has been moved INTO the loop to pull appropriate .sli and ndgsi files
            ; for the entire scene.

            sz = solarzenith[i,j]

            ; Pull the appropriate ndgsi and sli files for a given set of modeled solar zenith angles
            ; zenith_values = [15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75]

            abdiff = abs( zenith_values - sz ) ; find the smallest difference
            mindiff = min( abdiff, min_subscript ) ; find the subscript that has the smallest difference
            SZA = zenith_values[min_subscript] ; pull SZA from vector

            ndgsilut(*, *) = ndgsiluts(min_subscript, *, *)

            ; These are the clean-spectra for MODIS per solar zenith angle.
            sli(*, *) = slis(min_subscript, *, *)

            ; --------------------- If the pixel is considered snow, radiative forcing calculations begin----------------

            if (ndgsi(i,j) gt ndgsilut(1,109)) then begin
              grsz(i,j) = ndgsilut(0,109)+((ndgsi(i,j)-ndgsilut(1,109))/(ndgsilut(1,109)-ndgsilut(1,108)))*10.0
              cleanspec = sli(*,109)  ; *** do not modify this spectrum
            endif else if (ndgsi(i,j) lt ndgsilut(1,0)) then begin
              grsz(i,j) = ndgsilut(0,0)
              cleanspec = sli(*,0)    ; *** do not modify this spectrum
            endif else begin
              lutminlist = where(reform(ndgsilut(1,*)) gt ndgsi(i,j),count)
              if count gt 0 then luthigh = min(lutminlist)
              lutmaxlist = where(reform(ndgsilut(1,*)) lt ndgsi(i,j),count)
              if count gt 0 then lutlow = max(lutmaxlist)
              grsz(i,j) = ndgsilut(0,lutlow)+((ndgsi(i,j)-ndgsilut(1,lutlow))/(ndgsilut(1,luthigh)-ndgsilut(1,lutlow)))*10.0
              ; Clean MODIS spectrum
              cleanspec = sli(*,lutlow) + ((ndgsi(i,j)-ndgsilut(1,lutlow))/(ndgsilut(1,luthigh)-ndgsilut(1,lutlow)))*(sli(*,lutlow)-sli(*,luthigh))

              ; Determine difference between clean MODIS spectrum and measured MODIS spectrum
              specratio = cleanspec(3)/rfl(3,i,j)
              cumwts(i,j) = total(cleanspec(0:2) - rfl(0:2,i,j)*specratio)
              weights = cleanspec(0:3) - rfl(0:3,i,j)*specratio
              weights = reform(weights)

              ; Fit MODIS spectrum to AVIRIS wavelengths
              splineweights = spline(MODISwvl(0:3),weights,AVIwvl(0:50))
              splineweights = splineweights / 10000.

              ; NOTE: passing in sz NOT sza, so exact irradiance spectrum is calculated
              Irrad = drfs_irradiance_v1_2(solar_zenith_angle=sz, elev=elev[i,j],$
		      cosine_illumination_angle=cosine_illumination_angle[i,j],$
                      dir_arr=dir_arr, dif_arr=dif_arr, ii=ii, jj=jj)

              ; Output validation site irradiance spectra *** AB commented out 4/22/13 ****
              ;if i eq SASP[0] and j eq SASP[1] then begin
              ;                            openw,1, strcompress('SASP_Irradiance.'+year+string(doy)+'.out',/remove)
              ;                             out = fltarr(2,216)
              ;                             out[0,*] = aviwvl
              ;                             out[1,*] = irrad
              ;                            printf,1, out
              ;                            close,1
              ;
              ;                            ;print, ((cleanspec(0:3) - rfl(0:3,i,j)*specratio) / cleanspec(0:3)) * 100. , ' percent difference '
              ;                          endif
              ;
              ;                          if i eq SBSP[0] and j eq SBSP[1] then begin
              ;                            openw,1, strcompress('SBSP_Irradiance.'+year+string(doy)+'.out',/remove)
              ;                             out = fltarr(2,216)
              ;                             out[0,*] = aviwvl
              ;                             out[1,*] = irrad
              ;                            printf,1,out
              ;                            close,1
              ;
              ;                            ;print, ((cleanspec(0:3) - rfl(0:3,i,j)*specratio) / cleanspec(0:3)) * 100. , ' percent difference '
              ;                          endif
              ;
              ;                           if i eq GMSP[0] and j eq GMSP[1] then begin
              ;                            openw,1, strcompress('GMSP_Irradiance.'+year+string(doy)+'.out',/remove)
              ;                             out = fltarr(2,216)
              ;                             out[0,*] = aviwvl
              ;                             out[1,*] = irrad
              ;                            printf,1, out
              ;                            close,1
              ;                          endif

              ; Difference between modeled and measured spectrum in VIS wavelenghts
              deltarad(i,j) = total(splineweights*irrad(0:50))/total(irrad(0:50))
              deltarad(i,j) = deltarad(i,j) * 100 ; radiance difference in percent

              ; *** Radiative forcing file ****
              radforc(i,j) = total(splineweights * irrad(0:50))

            endelse
          endelse
        endfor
      endfor

      ; ------------------------ Check irradiance and clean spectrum -------------------------------

      ; window,3
      ; wshow,3
      ; plot, irrad, yrange=[0,20],background = 255, color = 50, thick = 3

      ; --------------------------------------------------------------------------------------------

      ; Create array for each different variable that was used to compute radiative forcing
      snowbundle = fltarr(ns,nl,7)
      snowbundle(*,*,0) = ndgsi
      snowbundle(*,*,1) = ndsi
      snowbundle(*,*,2) = snow
      snowbundle(*,*,3) = grsz
      snowbundle(*,*,4) = cumwts
      snowbundle(*,*,5) = deltarad
      snowbundle(*,*,6) = radforc

      RETURN, SNOWBUNDLE

    endif
  endif
END


; ####################################################################################################
; ####################################################################################################
; ####################################################################################################

PRO MOD_DRFS_v1_2, dir=dir,comps_dir=comps_dir,file=file,outfile=outfile,zenithfile=zenithfile,$
    azimuthfile=azimuthfile,ns=ns,nl=nl,nb=nb,date=date,year=year,h=h,v=v,thresh=thresh
;
; MOD_DRFS_V1_1 is the first program, in a series of programs and functions,
; to compute the radiative forcing by dust on snow using MODIS data. It can
; be called on its own for single tiles or used with modloop_v1_1.pro for multiple tiles.
;
; INPUTS:
;
; dir         = Root directory for files, e.g. dir='/usr/local/snow/data/jobs/symlinks/MODSCAG/'
; comps_dir   = Root directory where data comonents reside
; file        = Input HDF file.
; zenithfile  = Input solar zenith file.
; azimuthfile = Input solar azimuth file.
; outfile     = Rootname of output files, e.g. 'MOD09GA.A2010001.h09v05'
; ns          = Number of Samples in MODIS image.
; nl          = Number of Lines in MODIS image.
; nb          = Number of Bands in MODIS image.
; date        = Day of year of input images, MUST BE 3 DIGITS i.e. 001, 002... 010, 011, ...100, 101
; year        = Year of input images.
; h           = Horizontal placement of MODIS tiles, e.g. for h09v05, h='9'
; v           = Vertical placement of MODIS tiles, e.g. for h09v05, v='5'
; thresh      = 1 if Vegetation threshold should be used, 0 if vegetation threshold should NOT be used.
;
; For example, at the command line:
;
; MOD_DRFS_v1_2_local, dir='/usr/local/snow/data/jobs/symlinks/MODSCAG/', comps_dir='/usr/local/snow/data/jobs/symlinks/MODSCAG/Components/',$
; file='MOD09GA.A2010137.h09v05.005.2010139141210.hdf', outfile='MOD09GA.A2010137.h09v05', zenithfile='MOD09GA.A2010137.h09v05.005.2010139141210.solarzenith_1.dat',$
; azimuthfile='MOD09GA.A2010137.h09v05.005.2010139141210.solarazimuth_1.dat', ns=2400, nl=2400, nb=7, date=141, year='2010', h='9', v='5', thresh = 0
;
; Post-processing can be called within the MOD_DRFS_v1_1.pro, however it is currently commented out, so we can follow the SCAG post-processing
; protocol.
;
; * Currently the code is setup for MODIS tiles h08v05, h09v04, h09v05, h10v05. If a new tile is added for the western US, the pull_dem_v1_1.pro
;   needs to be updated with the UL coorder coordinates of the new MODIS tile.
;
; Intro comments inserted: AB 2/28/12
;
; Modified to use HDF as input for surface reflectance files: AB 9/3/13
; ___________________________________________________________________

  start = systime(1)

  Print, ' '
  Print, ' ---------- Processing File:   ', file ,'   Starting at:   ' , systime(0), ' ----------'

; ---------------------- Open Geometry Files ------------------------

; ***** TO DO:  Each of these openr statement uses the DIR file location, this will need to be adapted to JPL file structure ************

; Extract bip array from hdf
  create_bip = extract_modis_reflectance(file, bip) ; HDF file needs full path.  Inserted by AB, 9/3/13

; Open solar zenith file
  openr,1,zenithfile
;  openr,1,dir+'/'+year+'/'+ zenithfile ; ***** TO DO: PATH *****
  solarzenith=intarr(ns,nl)
  readu,1,solarzenith
  close,1

; Open solar azimuth file
  openr,1,azimuthfile
;  openr,1,dir+'/'+year+'/'+ azimuthfile ; ***** TO DO: PATH *****
  solarazimuth=intarr(ns,nl)
  readu,1,solarazimuth
  close,1

 ; Open slope and aspect file
  terrain_file = strcompress(comps_dir + 'DEM/terrain_*_h*'+h+'v*'+v+'.bsq',/remove) ; new naming convention (9.13.13) for AK DEMs: ab

  terrain_input = fltarr(ns,nl,2)
  openr,1,terrain_file
  readu,1,terrain_input
  close,1

; Pull slope and aspect from terrain files
  slope = terrain_input[*,*,0]
  aspect = terrain_input[*,*,1]

  dem_input = strcompress(comps_dir + 'DEM/dem_*_h*'+h+'v*'+v+'.bsq',/remove)

  openr, 1, dem_input
  dem = intarr(ns,nl)
  readu,1,dem
  close,1

; Open irradiance arrays created with SBDART

  restore, comps_dir + '/CRB/direct' ; ***** TO DO: PATH *****
  restore, comps_dir + '/CRB/total'  ; ***** TO DO: PATH *****

; Match size of solar zenith and azimuth files to ns, nl of MODIS surface reflectance image
  ;solarzenith  = congrid(solar_zenith_input,ns,nl)  ; Not NEEDED if using SCAG pre-processed data
  ;solarazimuth = congrid(solar_aspect_input,ns,nl)

; ----------------------- Pull DEM for the appropriate MODIS tiles--------------------------------

;                     REMOVED THIS PIECE OF CODE - ALL DEMs HAVE BEEN PRE-PROCESSED

 ;********************************  FILE PRE-PROCESS STEPS *****************************

; MODIS creates the solar geometry files as 4 digit whole numbers,
; i.e. 2453 equals 24.53 degrees

  solarzenith *= 0.01

  solarazimuth *= 0.01

; IDL triginometric calculations use radians, thus all solar and terrain files used to correct irradiance must be in radians.

  deg_to_rad = !pi/180.

  slope_rad     = slope * ( deg_to_rad )
  aspect_rad    = aspect * ( deg_to_rad )

  solar_az_rad  = solarazimuth * ( deg_to_rad )
  sza_rad       = solarzenith * ( deg_to_rad )

; Calculate cosine illumination angle

  cos_slope_rad    = cos(slope_rad)
  sin_slope_rad    = sin(slope_rad)

  cos_sza_rad      = cos(sza_rad)
  sin_sza_rad      = sin(sza_rad)

  cosine_illumination_angle = cos_sza_rad * cos_slope_rad + sin_sza_rad * sin_slope_rad * cos(solar_az_rad - aspect_rad)

; Check math:  Calculation of Illumination Angle
    ;I = acos(cos(sza_rad)*cos(slope_rad)+sin(sza_rad)*sin(slope_rad)*cos(solar_az_rad - aspect_rad))
    ;print, I*(180/!pi) , ' Illumination angle degrees'

; SBDART computed irradiance based on elevation in km above sea level,
; thus dem values need to be in km

  elev = FIX(dem * 0.001)

  solarzenith = FIX(solarzenith) ; need a solar zenith angle NOT in radians to pull SBDART file

; *************************** OPEN SBDART FILES ***************************************

; -------------------------------- Prepare Irradiance Files---------------------------------
;  The 'total' and 'direct' irrays were created using the SBDART.z5to70.txt file (SBDART.z5to70.cmd),
;  which is an output from SBDART. I read SBDART.z5to70.txt using read_ascii and pulled out the total
;  and direct columns from the .txt file.  Then saved these variables.  Thus, if new SBDART runs are
;  created, the total and direct variables will have to be created again using read_ascii. (ab:1/10/12)

; Create diffuse array from total and direct
   diffuse = total - direct

; Reform Arrays to Bips

  dir_arr = reform(direct,216,14,19)  ; Direct incomming spectral irradiance

  dif_arr = reform(diffuse,216,14,19)  ; Diffuse incomming spectral irradiance

;------------------------------ Calculating Radiative Forcing -----------------------------

; If all works in mod09ga_force_weight_v# this will change to a value of 1: (COMMENTED OUT AB: 2/4/13)
;  success=0

  snowbundle1 = mod09ga_force_weight_v1_2(comps_dir=comps_dir, rfl=bip, ns=ns, nl=nl ,nb=nb, locale='crb',$;  NO MORE, success=success,$
                                          solarzenith=solarzenith, elev=elev, cosine_illumination_angle=cosine_illumination_angle, dir_arr=dir_arr,$
                                          dif_arr=dif_arr, thresh=thresh, year=year, doy=date, h=h, v=v)

 ; IF success EQ 1 THEN BEGIN ; COMMENTED OUT AB: 2/4/13

    ndgsi1 = reform(snowbundle1(*,*,0))
    ndsi1  = reform(snowbundle1(*,*,1))
    snow1  = reform(snowbundle1(*,*,2))
    grnsz1 = reform(snowbundle1(*,*,3))
    cumwts1 = reform(snowbundle1(*,*,4))    ;
    deltarad1 = reform(snowbundle1(*,*,5))  ;
    radforc1 = reform(snowbundle1(*,*,6))   ;

print, ' Successful return of snowbundle at:            ' , systime(0)
    ; removed cloudmask here

; -------------------------------- Outputting Files -----------------------------------

Print, ' Writing outfiles '
Print, ' '

; This variable was added by CGOODALE, path updated by ab: 2/4/12, not sure where we're using it.
  archive_path = dir+'/' ; **** TO DO: PATH ****

; Writes the snowbundle array, deltarad, and forcing files created with the mod09ga_force_weight function.
; 5/7/13 A.B. - I am commenting out snowbundle output.

;  openw, U, archive_path + outfile+'.forcing.bundle.img', /get_lun
;  writeu,U, snowbundle1
;  Free_lun,U

  ; In final format, these should be cloud-maksed, de-striped geo-tiffs

  openw, U, archive_path + outfile+'.deltavis.dat', /get_lun  ;  ********** NEEDS POSTPROCESSING *************
  writeu,U, deltarad1
  Free_lun,U

  openw, U, archive_path + outfile+'.forcing.dat', /get_lun ;  ********** NEEDS POSTPROCESSING *************
  writeu,U, radforc1
  Free_lun,U

; 5/7/13 A.B. - I am commenting out .drfs.sca.dat output.
;  openw, U, archive_path + outfile+'.drfs.sca.dat', /get_lun
;  writeu,U, snow1
;  Free_lun,U

  openw, U, archive_path + outfile+'.drfs.grnsz.dat', /get_lun
  writeu,U, grnsz1
  Free_lun,U

; **************************************************************************************

 ; ENDIF

; ------------------------------------ DONE-ZO ------------------------------------------

  endall = systime(1)
  total_elapsed = endall - start

print, ' ******  Finished processing in:  ', total_elapsed/60, '   minutes *********'

END
