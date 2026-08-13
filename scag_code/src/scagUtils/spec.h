/*
 * spec.h - General specifications used by scag programs
 *
 * 14-Jul-2021 M. J. Brodzik brodzik@nsidc.org 303-492-8263
 * Copyright (C) 2021 Regents of the University of Colorado
 */
#ifndef spec_H
#define spec_H

/* System libraries */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <math.h>
#include <ctype.h>

/* General settings */
#define TRUE 1
#define FALSE 0
#define MDOS TRUE

#ifdef MDOS
  typedef unsigned char CHAR;
  typedef unsigned INT;
#endif

/* FIXME: these should be standard C math functions */
#define maxval(A,B) ((A) > (B) ? (A): (B))
#define minval(A,B) ((A) < (B) ? (A): (B))
#define sqr(A) (A)*(A)

/* Prototype all functions */
/* FIXME: These should be separated into .h/.c file pairs */

/* Function Group USERINT */
void getfilenames(char *filename,char *query);
void box( int row, int col, int rowLast, int colLast );
unsigned GetKey( int fWait );
int selectspeclist(int nnames, int nrows, int ncols,
     int colwidth, int srow, int scol, char *list[],
     int *specloc, int *pointer,int screenwidth, int *spec,
     int *colorval,int screenheight);
void displaynames(int first, int last, char *list[], int scol,
	int ncols, int colwidth, int *ccol,
	int *crow, int *spec, int *colorval);
int selectbands(int nbands, int nrows, int ncols,
     int colwidth, int srow, int scol, int *bndlist,
     int *specloc,int screenwidth,int screenheight);
int datarange(int nbands,char *search,int *list,int *spec);
int buildnumber(int count, char *buf);
int power(int base, int number);
void selectreflist(int nnames, int nrows, int ncols,
     int colwidth, int srow, int scol, char *list[],
     int *specn, int *pointer, int screenwidth,int screenheight);
void printmessage(char *buf,int row, int col, int tcol, int nerase);
int getfilelist(char *list[], char *queery,char *path);
int selectbandpairs(int nbands,int nrows, int ncols,
      int colwidth, int srow, int scol, int *bndlist,
      int *specloc, int screenwidth,int screenheight);
int selectcolorspeclist(int nnames, int nrows, int ncols,
     int colwidth, int srow, int scol, char *list[],
     int *specloc, int *pointer,int screenwidth, int *spec,
     int *colorval,int screenheight);
void padstring(int longlength,char *buf);
void choosemenu(int nitems,char *itemlist[],int *spec);
int readasciiline(FILE *fp1,char *buf,int llength);
void printerror(char *message, int xloc, int yloc);

/* Function Group FILEOPS */
void scag_getline(int fd,int line,long width,int *array,long hdrsize);
int openread(char *fname);
void specheader(int fd,int nspec,int nbands,char *datatype,int gain,
 char *compress,int *ar,char *fname);
void printheader(int nfile,int nbands,char *datatype,int gain,char *compress,
  int tcol,int trow,char *specname);
void readheader(int fd,int *nfile,int *nbands,char *datatype,int *gain,
  char *compress,short *array);
void writeline(int fd,int line,long width,int *array,long hdrsize);
int openwrite(char *fname);
void specsubset(int newbnds,int *outspec,int *bndloc);
void swpbytes(int *array,int num);
void imageheader(int fd,int xsize,int ysize,short *ar,
     char *fname, long headersize);
void writebytes(int fd,int line,INT width,CHAR *array,long hdrsize);

/* Function Group MGSMIX */
float mgsmix(int nbands, float *emspec[], int nem, float *p[]);
float calcfractions(int nbands, float *emspec[], float *ldata,int ne,
    float *fractions, float *resid,float *p[]);
/* Standalone Function GETDIR */
void getdir(char *buf, char *filelist[], int *fcount);
/* Standalone Function GETOUTFILE */
void getoutfile(char *filename,char *query);
/* Standalone Function GETSPECLIST */
void getspeclist(int fd, int nspec, int nbands, char *specname,
     char *list[], int *nselect, int *specloc, int *ar);
/* Standalone Function SELECTEM */
int selectem(int fd1, int fd2,int *em,
      int *emloc, int *libloc, int *nlib, char *emfile,
      char *libfile);
/* Standalone Function SELECTSP */
int selectsp(int fd1, int *outspec,
      int *bndloc, int *specloc, int *nsubsel, char *bflag);
/* Standalone Function SELECTAVG */
int selectavg(int fd1, int *libloc[], int *nlib,char *libfile,
     char *names[],int *lib);
/* AVIRIS Functions */
void stretch16bitto8(int *ar,int *lut,CHAR *bytedat,int npix,int gain);
void hist16bit(int *array,int *hist16,int sample,int npix,int gain);
void buildavirisspec(int xdim,int xloc, int *iar,int *oar[],
      int loc,long bpb,int spechdr);
int subsetaviris(int *outspec,int xstart,int xsize,long bpbuf,int nsamps);
/* MODIS Geographic Functions */
int waterflag(int nbands, float *ldata, int wtrmaxrfl);

#endif // spec_H
