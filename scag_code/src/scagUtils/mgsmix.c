/* Mgsmix.c : Mgsmix.c is a program that calculates the linear
   fractions given the spectral properties of an unknown and the 
   spectral properties of the endmembers using modified gramm-schmidt
   orthogonolization

*/
#include "scag_limits.h"
#include "spec.h"

	float mgsmix(int nbands, float *emspec[], int nem, float *p[])

     {
	float r[MAXEMS][MAXEMS],s[MAXEMS][MAXEMS],sum,rf;
	int i,j,k,n;

	n = nem-1;
	for (i=0;i<n;i++)
		for (j=0;j<nbands;j++)
			emspec[i][j]=emspec[i][j]-emspec[nem-1][j];

	for (i=0;i<nem;i++)
		for (j=0;j<nem;j++) {
			s[i][j]=0;
			r[i][j]=0;
		}


	for (i = 0; i <n;i++) {
		for (j=0;j<nbands;j++)
			r[i][i] = r[i][i]+emspec[i][j]*emspec[i][j];
		r[i][i] = sqrt(r[i][i]);
		for (j=0;j<nbands;j++)
			emspec[i][j] = emspec[i][j]/r[i][i];
		for (k=1+i;k<n;k++) {
			for (j=0;j<nbands;j++)
				r[i][k]=r[i][k]+emspec[i][j]*emspec[k][j];
			for (j=0;j<nbands;j++)
				emspec[k][j]=emspec[k][j]-emspec[i][j]*r[i][k];
		}
	}

	rf =1.0;
	for (i=0;i<n;i++){
		if (fabs(r[i][i]) <=0)
			rf = 0.0;
		else {
		    s[i][i]=1/r[i][i];
		    for (j=i+1;j<n;j++)
			s[j][i]=0.0;
		}
	}
	if (rf == 1.0) {
		for (i=1;i<n;i++){
			for (j=i-1; j>=0;j--) {
				sum=0.0;
				for (k=j+1;k<i+1;k++)
					sum = sum + r[j][k]*s[k][i];
				s[j][i]=-sum/r[j][j];
			}
		}
		for (i=0; i<n;i++) {
			for (j=0; j<nbands;j++) {
				p[i][j]=0.0;
				for (k=0; k<n;k++)
					p[i][j] = p[i][j]+s[i][k]*emspec[k][j];
			}
		}
	}

	return rf;
     }

float calcfractions(int nbands, float *emspec[], float *ldata, int ne,
		    float *fractions, float *resid,float *p[]) {

  float rms,f,tmp;
  int i,j,n,k;

  n = ne - 1;

  for (i = 0 ; i < ne; i++)
    fractions[i] = 0.0;

  for (i = 0; i < n; i++) {
    for (j=0; j < nbands;j++) {
      fractions[i] = fractions[i] + ldata[j] * p[i][j];
    }
  }

  f = 0;
  rms = 0.0;
		
  /* Save the shade fraction = 1 - sum(non shade EMs) */
  for (i = 0; i < n;i++)
    f = f + fractions[i];
  fractions[n] = 1 - f;

  /*
   * Do not allow any endmember fraction
   * (including shade) to be negative
   */
  for (i = 0; i < ne; i++) { 
    if ( fractions[i] < 0.0 ) {
      fractions[i] = 0.0;
    }
  }
			
  for (j = 0; j < nbands; j++) {
    tmp = 0;
    for (k = 0; k < n; k++)
      tmp = tmp + fractions[k] * emspec[k][j];
    resid[j] = ldata[j] - tmp;
    rms = rms + resid[j] * resid[j];
  }

  rms = sqrt(rms / nbands);
  
  return rms;

}

