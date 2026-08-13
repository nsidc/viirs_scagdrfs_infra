/* shdnorm.c - program to take an array of endmember fractions and compute
	       the shade-normalized fractions of the non-shade endmembers.
*/

#include "spec.h"

void shdnorm(float *fract, int ne, float *snfract)
{

   int i;
   float denom;

   /*
    * denominator - sum of non-shade spectral fractions, same as
    *               1 - fract[shade]
    */
   denom = 1.0 - fract[ne - 1];
   
   /* If all shade, prevent divide by zero */
   if ( denom == 0.0 ) {

     fprintf(stderr, "shnorm WARNING: pixel all shade, avoiding div by zero\n");
     denom = 1.0;

   }

   /* compute shade-normalized fraction for each non-shade EM */
   for ( i = 0; i < ne - 1; i++ ) {
     snfract[i] = fract[i] / denom;
   }

   return;

}
