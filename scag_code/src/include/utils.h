/*
 * utils.h - General utilities for scag programs
 *
 * 25-Oct-2019 M. J. Brodzik brodzik@nsidc.org 303-492-8263
 * Copyright (C) 2019 Regents of the University of Colorado
 */
#ifndef utils_H
#define utils_H

void utils_buildbilspec(short *oar,short *iar[],int npix,int nbands);
void utils_buildbipspec(short *iar,short *oar[],int npix,int nbands);
int utils_exit_error( char *msg );

#endif // utils_H
