/*
  tmsort
   
  Original
  Copyright (C) 2002 T. H. Painter
  Modifications and revisions:
  Copyright (C) 2019 Regents of University of Colorado
*/

/* System dependencies */
#include <argp.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>


/* Local dependencies */
#include "scag_limits.h"
#include "utils.h"

#define NODATA (-9999.0)

#define MINPERCENT (0)
#define MAXPERCENT (100)
#define SCALEPERCENT (100.0)
#define NODATAPERCENT (255)

#define MINRMS (0)
#define MAXRMS (255)
#define SCALERMS (1.0)
#define NODATARMS (UINT8_MAX)

#define MINGRAINSIZE (0) /* microns */
#define MAXGRAINSIZE (1600) /* microns */
#define SCALEGRAINSIZE (1.0)
#define NODATAGRAINSIZE (UINT16_MAX)

uint8_t flt2uchar( float in_value,
		   float in_nodata,
		   float scale_factor,
		   uint8_t out_nodata,
		   uint8_t out_min,
		   uint8_t out_max);

uint16_t flt2ushort( float in_value,
		     float in_nodata,
		     float scale_factor,
		     uint16_t out_nodata,
		     uint16_t out_min,
		     uint16_t out_max);

/* Global variables required by argument parser */
const char *argp_program_version = "tmsort v2.0";
const char *argp_program_bug_address = "<brodzik@colorado.edu>";
static char doc[] =
  "tmsort merges output from multiple control scag runs\n"
  "    by iterating through series of 2 to 6 endmember models \n"
  "    created by tmscag. Results are sorted according to priorities \n"
  "    into optimized image outputs.\n"
  "  2EMFILE - filename with list of 2-endmember model prefixes\n"
  "  3EMFILE - filename with list of 3-endmember model prefixes\n"
  "  PRIORITYFILE2 - filename with list priority classes \n"
  "    for each 2-endmember models\n"
  "  PRIORITYFILE3 - filename with list priority classes \n"
  "    for each 3-endmember models\n"
  "  OUTPUTFORM - string prefix for output files\n"    
  "  NSAMPLES - number of image samples\n"
  "  NLINES - number of image lines\n"
  "  \n"
  "  Outputs are:\n"
  "  1) rms, fractional snow, veg, rock, other, shade, grain size\n"
  "  2) (only if -m option is invoked)  mask image of\n"
  "     1s (pixel modeled) or 0s (pixel not modeled)\n"
  "  Models are assessed on priority given upon input and RMS within a given \n"
  "  priority.  CHECKME:  Pixels indicated as flagged with -9999 \n"
  "  (not modeled) are attributed the value -9999.0 in the ultimate image.\n";

/* description of arguments */
static char args_doc[] = "2EMFILE 3EMFILE PRIORITYFILE2 PRIORITYFILE3 "
  "OUTPUTFORM NSAMPLES NLINES";

/* options */
static struct argp_option options[] =
  {
    {"mask",    'm', 0,      0,   "Save mask output (default is no mask)" },
    {"verbose", 'v', 0,      0,   "Produce verbose output" },
    { 0 }
  };

/* used to communicate with parse_opt */
struct arguments
{
  char *args[7];
  int mask;
  int verbose;
};
				       
/* parse a single option */
static error_t parse_opt(int key, char *arg, struct argp_state *state)
{
  /*
   * Get the input argument from argp_parse, which is a pointer to
   * our arguments structure
   */
  struct arguments *arguments = state->input;

  switch (key)
    {
    case 'm':
      arguments->mask = 1;
      break;
      
    case 'v':
      arguments->verbose = 1;
      break;
      
    case ARGP_KEY_ARG:
      if (state->arg_num >= 7)
	/* Too many arguments */
	argp_usage(state);

      arguments->args[state->arg_num] = arg;

      break;

    case ARGP_KEY_END:
      if (state->arg_num < 7)
	/* Not enough arguments */
	argp_usage(state);

      break;

    default:
      return ARGP_ERR_UNKNOWN;
    }
  
  return 0;
  
}

/* our argp parser */
static struct argp argp = { options, parse_opt, args_doc, doc };

int main( int argc, char **argv)
{

  int i,j,k,l;
  int n2em,n3em,nummod,prrty2[MAX2EMS],prrty3[MAX3EMS];
  int minprrty;
  int SAMPLES, LINES;

  /* TODO: make these hardcoded values MAXSTRING */
  char file2em[100], file3em[100];
  char outfile[100];
  char errmsg[MAXSTRING];

  float gr[MAXSAMPLES],gr2[MAX2EMS][MAXSAMPLES],gr3[MAX3EMS][MAXSAMPLES];
  float rms[MAXSAMPLES],rms2[MAX2EMS][MAXSAMPLES],rms3[MAX3EMS][MAXSAMPLES];
  float snow[MAXSAMPLES],snow2[MAX2EMS][MAXSAMPLES],snow3[MAX3EMS][MAXSAMPLES];
  float veg[MAXSAMPLES],veg2[MAX2EMS][MAXSAMPLES],veg3[MAX3EMS][MAXSAMPLES];
  float rock[MAXSAMPLES],rock2[MAX2EMS][MAXSAMPLES],rock3[MAX3EMS][MAXSAMPLES];
  float other[MAXSAMPLES],other2[MAX2EMS][MAXSAMPLES],other3[MAX3EMS][MAXSAMPLES];
  float shade[MAXSAMPLES],shade2[MAX2EMS][MAXSAMPLES],shade3[MAX3EMS][MAXSAMPLES];
  float minrms;

  unsigned char mask[MAXSAMPLES],mask2[MAX2EMS][MAXSAMPLES],mask3[MAX3EMS][MAXSAMPLES];

  /* output buffers */
  uint8_t out_snow[MAXSAMPLES];
  uint8_t out_veg[MAXSAMPLES];
  uint8_t out_rock[MAXSAMPLES];
  uint8_t out_other[MAXSAMPLES];
  uint8_t out_shade[MAXSAMPLES];
  uint8_t out_rms[MAXSAMPLES];
  uint16_t out_gr[MAXSAMPLES];

  FILE *fp2,*fp3,*fpprrty2,*fpprrty3;
  FILE *fpgr2[MAX2EMS],*fprms2[MAX2EMS],*fpsnow2[MAX2EMS],*fpveg2[MAX2EMS];
  FILE *fprock2[MAX2EMS],*fpother2[MAX2EMS],*fpshade2[MAX2EMS];
  FILE *fpmask2[MAX2EMS];
  FILE *fpgr3[MAX3EMS],*fprms3[MAX3EMS];
  FILE *fpsnow3[MAX3EMS],*fpveg3[MAX3EMS],*fprock3[MAX3EMS],*fpother3[MAX3EMS];
  FILE *fpshade3[MAX3EMS],*fpmask3[MAX3EMS];
  FILE *fpsnow,*fpveg,*fprock,*fpother,*fpshade,*fpgr,*fprms,*fpmask;

  struct arguments arguments;

  /* Default values */
  arguments.verbose = 0;
  arguments.mask = 0;
   
  argp_parse (&argp, argc, argv, 0, 0, &arguments);
   
  sscanf(arguments.args[5], "%d", &SAMPLES);
  sscanf(arguments.args[6], "%d", &LINES);

  /* Ensure inputs are within expected bounds */
  if ( SAMPLES > MAXSAMPLES )
    {
      sprintf(errmsg, "%s: Error SAMPLES=%d must be <= %d\n",
	      __FILE__, SAMPLES, MAXSAMPLES);
      utils_exit_error(errmsg);
    };
  if ( LINES > MAXLINES )
    {
      sprintf(errmsg, "%s: Error LINES=%d must be <= %d\n",
	      __FILE__, LINES, MAXLINES );
      utils_exit_error(errmsg);
    };

  if ( arguments.verbose )
    {
      fprintf(stderr, "> %s: 2EMFILE = %s\n", __FILE__, arguments.args[0]);
      fprintf(stderr, "> %s: 3EMFILE = %s\n", __FILE__, arguments.args[1]);
      fprintf(stderr, "> %s: PRIORITYFILE2 = %s\n", __FILE__, arguments.args[2]);
      fprintf(stderr, "> %s: PRIORITYFILE3 = %s\n", __FILE__, arguments.args[3]);
      fprintf(stderr, "> %s: OUTPUTFORM = %s\n", __FILE__, arguments.args[4]);
      fprintf(stderr, "> %s: NSAMPLES = %d\n", __FILE__, SAMPLES);
      fprintf(stderr, "> %s: NLINES = %d\n", __FILE__, LINES);
      fprintf(stderr, "> %s: -m = %d\n", __FILE__, arguments.mask);
    }

  //  OPEN COMMAND LINE FILES
  if ( !(fp2 = fopen(arguments.args[0],"r")) )
    {
      sprintf(errmsg, "%s: Error opening %s: %s\n",
	      __FILE__, arguments.args[0], strerror(errno));
      utils_exit_error(errmsg);
    };
  printf("%s opened\n",arguments.args[0]);

  if ( !(fp3 = fopen(arguments.args[1],"r")) )
    {
      sprintf(errmsg, "%s: Error opening %s: %s\n",
	      __FILE__, arguments.args[1], strerror(errno));
      utils_exit_error(errmsg);
    };
  printf("%s opened\n",arguments.args[1]);
   
  if ( !(fpprrty2 = fopen(arguments.args[2],"r")) )
    {
      sprintf(errmsg, "%s: Error opening %s: %s\n",
	      __FILE__, arguments.args[2], strerror(errno));
      utils_exit_error(errmsg);
    };
  printf("%s opened\n",arguments.args[2]);

  if ( !(fpprrty3 = fopen(arguments.args[3],"r")) )
    {
      sprintf(errmsg, "%s: Error opening %s: %s\n",
	      __FILE__, arguments.args[3], strerror(errno));
      utils_exit_error(errmsg);
    };
  printf("%s opened\n",arguments.args[3]);

  //  2 ENDMEMBER MODELS
  fscanf(fp2,"%d",&n2em);
  for (i=0;i<n2em;i++)
    {
      fscanf(fp2,"%s",file2em);
      sprintf(outfile,"%ssnow.pic\0",file2em);      // snow
      fpsnow2[i]=fopen(outfile,"r");
      sprintf(outfile,"%sveg.pic\0",file2em);       // vegetation
      fpveg2[i]=fopen(outfile,"r");
      sprintf(outfile,"%srock.pic\0",file2em);      // rock
      fprock2[i]=fopen(outfile,"r");
      sprintf(outfile,"%sother.pic\0",file2em);     // other
      fpother2[i]=fopen(outfile,"r");
      sprintf(outfile,"%sshade.pic\0",file2em);     // shade
      fpshade2[i]=fopen(outfile,"r");
      sprintf(outfile,"%sgrnsz.pic\0",file2em);     // grain size
      fpgr2[i]=fopen(outfile,"r");
      sprintf(outfile,"%srms.pic\0",file2em);       // rms error
      fprms2[i]=fopen(outfile,"r");
      sprintf(outfile,"%smask.pic\0",file2em);      // mask
      fpmask2[i]=fopen(outfile,"r");
      printf("2 ENDMEMBER MODEL FILES OPENED\n");
    }

  //  3 ENDMEMBER MODELS
  fscanf(fp3,"%d",&n3em);                       // number 
  for (i=0;i<n3em;i++)
    {
      fscanf(fp3,"%s",file3em);
      printf("opening %s\n",file3em);
      sprintf(outfile,"%ssnow.pic\0",file3em);   // snow
      fpsnow3[i]=fopen(outfile,"r");
      sprintf(outfile,"%sveg.pic\0",file3em);    // vegetation
      fpveg3[i]=fopen(outfile,"r");
      sprintf(outfile,"%srock.pic\0",file3em);   // rock
      fprock3[i]=fopen(outfile,"r");
      sprintf(outfile,"%sother.pic\0",file3em);  // other
      fpother3[i]=fopen(outfile,"r");
      sprintf(outfile,"%sshade.pic\0",file3em);  // shade
      fpshade3[i]=fopen(outfile,"r");
      sprintf(outfile,"%sgrnsz.pic\0",file3em);  // grain size
      fpgr3[i]=fopen(outfile,"r");
      sprintf(outfile,"%srms.pic\0",file3em);    // rms error
      fprms3[i]=fopen(outfile,"r");
      sprintf(outfile,"%smask.pic\0",file3em);   // mask
      fpmask3[i]=fopen(outfile,"r");
    }
  printf("3 ENDMEMBER MODEL FILES OPENED\n");

  //  READ PRIORITY DATA
  for (i=0;i<n2em;i++)
    {
      fscanf(fpprrty2,"%d",&prrty2[i]);
      printf("2em prty %d = %d\n",i,prrty2[i]);
    }
  for (i=0;i<n3em;i++)
    {
      fscanf(fpprrty3,"%d",&prrty3[i]);
      printf("3em prty %d = %d\n",i,prrty3[i]);
    }
  printf("PRIORITY DATA READ\n");

  //  OPEN OUTPUT FILES
  sprintf(outfile,"%ssnow.bin\0",arguments.args[4]);
  fpsnow=fopen(outfile,"w");
  sprintf(outfile,"%sveg.bin\0",arguments.args[4]);
  fpveg=fopen(outfile,"w");
  sprintf(outfile,"%srock.bin\0",arguments.args[4]);
  fprock=fopen(outfile,"w");
  sprintf(outfile,"%sother.bin\0",arguments.args[4]);
  fpother=fopen(outfile,"w");
  sprintf(outfile,"%sshade.bin\0",arguments.args[4]);
  fpshade=fopen(outfile,"w");
  sprintf(outfile,"%sgrnsz.bin\0",arguments.args[4]);
  fpgr=fopen(outfile,"w");
  sprintf(outfile,"%srms.bin\0",arguments.args[4]);
  fprms=fopen(outfile,"w");
  if (arguments.mask)
    {
      sprintf(outfile,"%smask.bin\0",arguments.args[4]);
      fpmask=fopen(outfile,"w");
    }
  printf("OUTPUT FILES OPENED\n");

  //  PROCESS DATA
  printf("Processing Line: ");
  for (i=0;i<LINES;i++)
    {
      if (0 == (i % 100)) {
	printf("%d...",i);
      }
      for (j=0;j<n2em;j++)
	{
	  fread(snow2[j],sizeof(float),SAMPLES,fpsnow2[j]);
	  fread(veg2[j],sizeof(float),SAMPLES,fpveg2[j]);
	  fread(rock2[j],sizeof(float),SAMPLES,fprock2[j]);
	  fread(other2[j],sizeof(float),SAMPLES,fpother2[j]);
	  fread(shade2[j],sizeof(float),SAMPLES,fpshade2[j]);
	  fread(gr2[j],sizeof(float),SAMPLES,fpgr2[j]);
	  fread(rms2[j],sizeof(float),SAMPLES,fprms2[j]);
	  fread(mask2[j],sizeof(unsigned char),SAMPLES,fpmask2[j]);
	}
      for (j=0;j<n3em;j++)
	{
	  fread(snow3[j],sizeof(float),SAMPLES,fpsnow3[j]);
	  fread(veg3[j],sizeof(float),SAMPLES,fpveg3[j]);
	  fread(rock3[j],sizeof(float),SAMPLES,fprock3[j]);
	  fread(other3[j],sizeof(float),SAMPLES,fpother3[j]);
	  fread(shade3[j],sizeof(float),SAMPLES,fpshade3[j]);
	  fread(gr3[j],sizeof(float),SAMPLES,fpgr3[j]);
	  fread(rms3[j],sizeof(float),SAMPLES,fprms3[j]);
	  fread(mask3[j],sizeof(unsigned char),SAMPLES,fpmask3[j]);
	}
      for (j=0;j<SAMPLES;j++)
	{

	  // INITIALIZE FIELDS
	  snow[j]=NODATA;   
	  veg[j]=NODATA;
	  rock[j]=NODATA;
	  other[j]=NODATA;
	  shade[j]=NODATA;
	  gr[j]=NODATA;
	  rms[j]=NODATA;
	  mask[j]=0;
	  minrms=10000.0;                   // finite rms limit
	  minprrty=100;                     // finite priority limit

	  // DATA REDUCTION
	  for (k=0;k<n2em;k++)
	    {
	      if (mask2[k][j] == 1)                // 2 endmembers worked
		{
		  if (rms2[k][j] < minrms && prrty2[k] < minprrty)
		    {
		      snow[j]=snow2[k][j];
		      veg[j]=veg2[k][j];
		      rock[j]=rock2[k][j];
		      other[j]=other2[k][j];
		      shade[j]=shade2[k][j];
		      gr[j]=gr2[k][j];
		      rms[j]=rms2[k][j];
		      mask[j]=mask2[k][j];
		      minrms=rms2[k][j];
		      minprrty=prrty2[k];
		    }
		}
	    }
	  for (k=0;k<n3em;k++)
	    {
	      if (mask3[k][j] == 1)          // 3 endmembers worked
		{

		  // model rms smaller: model priority higher (value lower)
		  if (rms3[k][j] < minrms && prrty3[k] < minprrty) 
		    {
		      snow[j]=snow3[k][j];
		      veg[j]=veg3[k][j];
		      rock[j]=rock3[k][j];
		      other[j]=other3[k][j];
		      shade[j]=shade3[k][j];
		      gr[j]=gr3[k][j];
		      rms[j]=rms3[k][j];
		      mask[j]=mask3[k][j];
		      minrms=rms3[k][j];
		      minprrty=prrty3[k];
		    }                           // minrms
		}                              // mask3
	    }                                 // k
	}                                    // j

      /*
       * Convert output from float to integer type
       */
      for ( j = 0; j < SAMPLES; j++ ) {
	out_snow[j] = flt2uchar( snow[j], NODATA, SCALEPERCENT,
				 NODATAPERCENT, MINPERCENT, MAXPERCENT);
	out_veg[j] = flt2uchar( veg[j], NODATA, SCALEPERCENT,
				NODATAPERCENT, MINPERCENT, MAXPERCENT);
	out_rock[j] = flt2uchar( rock[j], NODATA, SCALEPERCENT,
				 NODATAPERCENT, MINPERCENT, MAXPERCENT);
	out_other[j] = flt2uchar( other[j], NODATA, SCALEPERCENT,
				  NODATAPERCENT, MINPERCENT, MAXPERCENT);
	out_shade[j] = flt2uchar( shade[j], NODATA, SCALEPERCENT,
				  NODATAPERCENT, MINPERCENT, MAXPERCENT);
	out_rms[j] = flt2uchar( rms[j], NODATA, SCALERMS,
				NODATARMS, MINRMS, MAXRMS);
	out_gr[j] = flt2ushort( gr[j], NODATA, SCALEGRAINSIZE,
				NODATAGRAINSIZE, MINGRAINSIZE, MAXGRAINSIZE);

	/*
	 * This is a bit of a sledgehammer: ensure that pixels with
	 * 0 % snow cover are setting grain size to NODATA.
	 * The "real" fix might better be to understand why this
	 * condition has been occurring in tmscag in the first place.
	 * With all outputs set to char/ushort types here, it is
	 * easier to enforce the relationship here.
	 */
	if ( MINPERCENT == out_snow[j] ) {
	  out_gr[j] = NODATAGRAINSIZE;
	}
	
      }

      fwrite( out_snow, sizeof(uint8_t), SAMPLES, fpsnow );
      fwrite( out_veg, sizeof(uint8_t), SAMPLES, fpveg);
      fwrite( out_rock, sizeof(uint8_t), SAMPLES, fprock);
      fwrite( out_other, sizeof(uint8_t), SAMPLES, fpother);
      fwrite( out_shade, sizeof(uint8_t), SAMPLES, fpshade);
      fwrite( out_rms, sizeof(uint8_t), SAMPLES, fprms);
      fwrite( out_gr,sizeof(uint16_t), SAMPLES, fpgr);
      if (arguments.mask) {
	fwrite( mask, sizeof(uint8_t), SAMPLES, fpmask);
      }
    }                                       // i
  printf("\ntmsort done\n");

  exit( EXIT_SUCCESS );

}

/*
 * flt2uchar - checks range of values for value and converts to output uchar
 *
 * input :
 *   in_value : float value to check
 *   in_nodata : float nodata value (assumes this value is smaller than
 *               any other possible values)
 *   scale_factor : float multiplicative scale factor
 *   out_nodata : uint8_t nodata value for output
 *   out_min : uint8_t scaled minimum value for output
 *   out_max : uint8_t scaled maximum value for output
 *
 * output : n/a
 *
 * result : scaled, rov-checked uint8_t for output
 */
uint8_t flt2uchar( float in_value,
		   float in_nodata,
		   float scale_factor,
		   uint8_t out_nodata,
		   uint8_t out_min,
		   uint8_t out_max)
{

  uint8_t out_value;
  float temp;
    
  /*
   *   - set out_value to no data
   *   - if in_value > in_nodata,
   *      - scale input
   *         if value < out_min, reset to out_min
   *         else if value > out_max, reset to out_max
   *      - set output value to nearest uint8_t
   */
  out_value = out_nodata;
  if ( in_value > in_nodata ) {
    temp = in_value * scale_factor;
    if ( temp <= out_min ) {
      out_value = out_min;
    } else if ( temp >= out_max ) {
      out_value = out_max;
    } else {
      /* round to nearest integer */
      out_value = (uint8_t) (temp + 0.5);
    }
  }

  return out_value;

}

/*
 * flt2ushort - checks range of values for value and converts to output ushort
 *
 * input :
 *   in_value : float value to check
 *   in_nodata : float nodata value (assumes this value is smaller than
 *               any other possible values)
 *   scale_factor : float multiplicative scale factor
 *   out_nodata : unsigned short nodata value for output
 *   out_min : unsigned short scaled minimum value for output
 *   out_max : unsigned short scaled maximum value for output
 *
 * output : n/a
 *
 * result : scaled, rov-checked unsigned short for output
 */
uint16_t flt2ushort( float in_value,
		     float in_nodata,
		     float scale_factor,
		     uint16_t out_nodata,
		     uint16_t out_min,
		     uint16_t out_max)
{

  uint16_t out_value;
  float temp;
    
  /*
   *   - set out_value to no data
   *   - if in_value > in_nodata,
   *      - scale input
   *         if value < out_min, reset to out_min
   *         else if value > out_max, reset to out_max
   *      - set output value to nearest unsigned char
   */
  out_value = out_nodata;
  if ( in_value > in_nodata ) {
    temp = in_value * scale_factor;
    if ( temp <= out_min ) {
      out_value = out_min;
    } else if ( temp >= out_max ) {
      out_value = out_max;
    } else {
      /* round to nearest integer */
      out_value = (uint16_t) (temp + 0.5);
    }
  }

  return out_value;

}

