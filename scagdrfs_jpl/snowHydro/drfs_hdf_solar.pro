PRO drfs_hdf_solar, in_file = in_file

; This procedure pulls, resamples, and writes out the Solar Zenith and Solar Azimuth
; files from the MOD09GA .hdf file.
; 
; AB: 6/4/13
; 
; ex: drfs_hdf_solar, in_file = 'MOD09GA.A2010147.h09v05.005.2010149130734.hdf'
; ********************************

; Determine the # of characters before 'hdf' in the file name
  find_pos = strpos(in_file, 'hdf',/reverse_search)

; Isolate begining of file name
  begin_name = strmid(in_file, 0, find_pos)

; SD names to pull from HDF file
  SD_Name = ['SolarZenith_1' , $
             'SolarAzimuth_1' ]

; Pull files from HDF
  Zenith = read_modis_tile(in_file, SD_NAME=SD_Name[0], data=out_Zenith)
  Azimuth = read_modis_tile(in_file, SD_NAME=SD_Name[1], data=out_Azimuth)
  
; Resample files to 2400 x 2400
  Solar_Zenith = congrid(out_zenith, 2400, 2400)
  Solar_Azimuth = congrid(out_azimuth, 2400, 2400)

; Write files
  openw, 1, strcompress(begin_name + sd_name[0] + '.dat' , /remove)
  writeu, 1, Solar_Zenith
  close, 1 

  openw, 1, strcompress(begin_name + sd_name[1] + '.dat' , /remove)
  writeu, 1, Solar_Azimuth
  close, 1 

END