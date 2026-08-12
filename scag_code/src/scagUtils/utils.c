/*
 * utils - General utilities for scag programs
 *
 * 25-Oct-2019 M. J. Brodzik brodzik@nsidc.org 303-492-8263
 * Copyright (C) 2019 Regents of the University of Colorado
 */
#include <stdio.h>
#include <stdlib.h>

#include "utils.h"

// Builds a band interleaved by line array for a single line of TM data from a BIP array
// TODO: Document this--allowing user to specify nbands makes it not specific to TM
void utils_buildbilspec(short *oar, short *iar[], int npix, int nbands) {
   int  i, j;
   long l;

   for (i = 0; i < npix; i++) {
      for (j = 0; j < nbands; j++) {
         l      = (long)npix * j + (long)i;
         oar[l] = iar[j][i];
      }
   }
}


// Builds a band interleaved by pixel array for a single line of TM data from a BIL array
// TODO: Document this--allowing user to specify nbands makes it not specific to TM
void utils_buildbipspec(short *iar, short *oar[], int npix, int nbands) {
   int  i, j;
   long l;

   l = 0;
   for (j = 0; j < npix; j++) {
      for (i = 0; i < nbands; i++) {
         oar[j][i] = iar[l];

		 /* SCAG .bip file expects non-negative values
		  * and has both missing and <0 values set to zero
		  */
		 if (oar[j][i] < 0) oar[j][i] = 0;

         l++;
      }
   }
}


/*
 * utils_exit_error - print an error message and error exit
 *
 * input:
 *   msg : char * error message
 *
 * output: n/a
 *
 * returns : exits program with EXIT_FAILURE
 *
 */
int utils_exit_error(char *msg) {
   fprintf(stderr, "ERROR: %s\n", msg);
   fflush(stderr);
   exit(EXIT_FAILURE);
}
