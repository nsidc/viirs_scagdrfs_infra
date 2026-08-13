#include "scag_limits.h"
#include "spec.h"
#include <sys/types.h>
#include <unistd.h>


extern char buf[MAXBUF];

/* TODO: change fd from int to FILE *
 */
      void scag_getline(int fd,int line,long width,int *array,long hdrsize)

	{
	long skipbyte;
	int nbytes;
	if (line ==1){
		skipbyte =0;
		if (lseek(fd,skipbyte,SEEK_SET) <0){
			printf("Seek failed in read");
			exit(-1);
		}
	}
	if (line > 1){
		skipbyte = ((long)line-2)*(long)width+hdrsize;
		if (lseek(fd,skipbyte,SEEK_SET) <0){
			printf("Seek failed in read");
			exit(-1);
		}
	}
	nbytes = read(fd, array, width);
	return;
}
int openread(char *fname)

{
	int fd;
        if ((fd = open(fname,O_RDONLY,0444)) == -1){
                printf("cp: can't open %s \n",fname);
                exit(-1);
        }
	return fd;
}

void specheader(int fd,int nspec,int nbands,char *datatype,int gain,
 char *compress,int *ar,char *fname)

{
	void writeline();

	ar[0]=nspec;
	ar[1]=nbands;
	strncpy((char *)(ar+2),datatype,2);
	ar[3]=gain;
	strncpy((char *)(ar+4),compress,2);
	strncpy((char *)(ar+5),fname,NAMELENGTH);
	writeline(fd,1,LIBHDRSIZE,ar,(long)LIBHDRSIZE);
	return;
}
void printheader(int nfile,int nbands,char *datatype,int gain,char *compress,
  int tcol,int trow,char *specname)
{

	printf("Nspec  Bands  Gain  Datatype  Compression  Library ");
	printf("%4d %6d %4d       %s           %s         %s       ",
		nfile,nbands,gain,datatype,compress,specname);
 }

void readheader(int fd,int *nfile,int *nbands,char *datatype,int *gain,
  char *compress,short *array)

{
	scag_getline(fd,1,LIBHDRSIZE,(int *)array,(long)LIBHDRSIZE);
	*nfile=array[0];
	*nbands=array[1];
	strncpy(datatype,(char *)(array+2),2);
	*gain=array[3];
	strncpy(compress,(char *)(array+4),2);
	printf("%d %d %d\n",array[0],array[1],array[3]);
	return;
}

  void writeline(int fd,int line,long width,int *array,long hdrsize)

	{
	long skipbyte;
	int nbytes;

	if (line ==1){
		skipbyte = 0;
		if (lseek(fd,skipbyte,SEEK_SET) <0){
			printf("Seek failed in write");
			exit(-1);
		}
	}
	if (line > 1){
		skipbyte = ((long)line-2)*(long)width+hdrsize;
		if (lseek(fd,skipbyte,SEEK_SET) <0) {
			printf("Seek failed in write");
			exit(-1);
		}
	}
	nbytes = write(fd,array,width);


	return;
	}

int openwrite(char *fname)

{
	int fd;
	if ((fd = creat(fname,0666)) == -1){
		printf("cp: can't create %s",fname);
		exit(-1);
	}
	return fd;
}

  void specsubset(int newbnds,int *outspec,int *bndloc)

    {

       int i,band;


	for (i=0;i<newbnds;i++) {
		band = bndloc[i];
		outspec[i+SPECHDR]=outspec[band+SPECHDR];
	}
    }

void swpbytes(int *array,int num)
	{
	int i,v;
	for (i = 0; i< num; i++) {
		v= array[i];
		array[i]=((v & 0x00ff) << 8)+((v & 0xff00) >> 8);
	}
	return;
}
  void imageheader(int fd,int xsize,int ysize,short *ar,
     char *fname, long headersize)
 {
	void writeline();

	ar[0]=xsize;
	ar[1]=ysize;
	strncpy((char *)(ar+2),fname,NAMELENGTH);
	writeline(fd,1,(int)headersize,ar,headersize);
}

  void writebytes(int fd,int line,INT width,CHAR *array,long hdrsize)

	{
	long skipbyte;
	int nbytes;

	if (line ==1){
		skipbyte = 0;
		if (lseek(fd,skipbyte,SEEK_SET) <0){
			printf("Seek failed in write\n");
			exit(-1);
		}
	}
	if (line > 1){
		skipbyte = ((long)line-2)*(long)width+hdrsize;
		if (lseek(fd,skipbyte,SEEK_SET) <0){
			printf("Seek failed in write\n");
			exit(-1);
		}
	}
	nbytes = write(fd,array,width);
 }

 char *
 scanline(char dest[], 	/*output - destination string */
	  int dest_len, /*input - space available in dest */
	  FILE *file)	/*input - file pointer */
 {
	/* Performs scan of line and determines whether it is the end of a line */
	if (fgets(dest, dest_len, file) == 0)
		dest[0] = '\0';
	/* Removes newline character if it is present */
	else if (dest[strlen(dest) - 1] == '\n')
		dest[strlen(dest) - 1] = '\0';

	return (dest);
}
