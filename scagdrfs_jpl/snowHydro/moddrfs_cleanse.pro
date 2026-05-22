pro moddrfs_cleanse,prefix=prefix,ns=ns,nl=nl,mod09ga=mod09ga, threshold=threshold

;	moddrfs_cleanse
;	
;	IDL program to clean up under and overflow of MODDRFS run 
;
;	Input	
;		prefix	= prefix for all of the MODSCAG output filenames
;		ns	= number of samples
;		nl	= number of lines
;		mod09ga = MOD09GA hdf file associated with the modscag outputs
;
;	Output
;		write new copies of the MODDRFS files with 'cleanse' added to 
;       the filename
;
;
;	OPEN ALL OF THE FILES THAT NEED TO BE CLEANSED
	; open forcing file
	openr,1,string(prefix+'.forcing.dat')
	forcing=fltarr(ns,nl)
	readu,1,forcing
	close,1

	; open deltavis file
        openr,1,string(prefix+'.deltavis.dat')
	deltavis=fltarr(ns,nl)
	readu,1,deltavis
	close,1

	; open DRFS grain size file
        openr,1,string(prefix+'.drfs.grnsz.dat')
	grnsz=fltarr(ns,nl)
	readu,1,grnsz
	close,1

;	CALL THE CLEANSE FUNCTION
	if 0 eq cleanse_scag( mod09ga, THRESHOLD=threshold, $
                              FORCING=forcing, $
                              DELTAVIS=deltavis, $
                              GRAIN_SIZE=grnsz ) then begin
                              ;  VERBOSE=do_verbose

;       WRITE OUT ALL OF THE CLEANSED FILES
        ; output forcing file
        openw,10,string(prefix+'.forcing.cleanse.dat')
        writeu,10,forcing
        close,10

        ; output deltavis file
        openw,10,string(prefix+'.deltavis.cleanse.dat')
        writeu,10,deltavis
        close,10

        ; output drfs.grnsz file
        openw,10,string(prefix+'.drfs.grnsz.cleanse.dat')
        writeu,10,grnsz
        close,10

        endif

end
	
